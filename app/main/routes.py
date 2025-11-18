"""
Routes for the main blueprint.

This blueprint implements a simple multi-step flow:
1) Select source and destination platforms
2) Enter source connection details (for ESXi we use pyvmomi)
3) Connect and list VMs -> select VMs
4) Start migration (stubbed)

Each route contains comments explaining where to extend functionality.
"""
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from . import bp

from ..vmware.client import list_vms_on_esxi, verify_credentials, VmwareConnectionError

# Import the migration script config updater
try:
    from ..esxi_to_proxmox_migration import update_esxi_config, update_selected_vms
except ImportError:
    update_esxi_config = None
    update_selected_vms = None

# Import Proxmox client
try:
    from ..proxmox.client import verify_proxmox_credentials, ProxmoxConnectionError
    from ..ssh_runner import start_remote_migration, get_job_status, SSHRunnerError
except ImportError:
    verify_proxmox_credentials = None
    ProxmoxConnectionError = None


@bp.route("/")
def index():
    """Landing page - choose source and destination platforms.

    For simplicity we show a couple of options. In future you can load these
    from a DB or config and include additional platforms.
    """
    platforms = ["esxi", "proxmox", "kvm", "other"]
    return render_template("index.html", platforms=platforms)


@bp.route("/select-platforms", methods=["POST"])
def select_platforms():
    """Save platform choices in session and proceed to source details form."""
    source = request.form.get("source")
    destination = request.form.get("destination")
    if not source or not destination:
        flash("Please choose both source and destination platforms.")
        return redirect(url_for("main.index"))

    session["platforms"] = {"source": source, "destination": destination}
    return redirect(url_for("main.source_details"))


@bp.route("/source-details", methods=["GET"])
def source_details():
    """Show a source connection form depending on the chosen platform.

    Currently we support ESXi; for other platforms you'd display different fields.
    """
    platforms = session.get("platforms")
    if not platforms:
        return redirect(url_for("main.index"))
    return render_template("source_details.html", source=platforms["source"]) 


@bp.route("/connect-source", methods=["POST"])
def connect_source():
    """Attempt to connect to the source and list VMs.

    Expects host, username, password in the POST form for ESXi.
    Uses `list_vms_on_esxi` which wraps pyvmomi calls.
    """
    platforms = session.get("platforms")
    if not platforms:
        return redirect(url_for("main.index"))

    src = platforms["source"]
    if src != "esxi":
        flash("Only ESXi source is implemented in this scaffold.")
        return redirect(url_for("main.source_details"))

    host = request.form.get("host")
    username = request.form.get("username")
    password = request.form.get("password")

    if not host or not username or not password:
        flash("Provide host, username, and password to connect.")
        return redirect(url_for("main.source_details"))

    # Try to list VMs using pyvmomi wrapper
    try:
        # First verify the credentials
        success, message = verify_credentials(host, username, password)
        if not success:
            # If AJAX request, return JSON error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, message=message), 400
            flash(message, "error")
            return redirect(url_for("main.source_details"))

        # ✓ AUTHENTICATION SUCCESSFUL - Update ESXi config variables in script
        if update_esxi_config:
            update_esxi_config(host, username, password)
            print(f"[INFO] ESXi configuration updated in script: {host}")

        # If credentials are valid, try to list VMs
        vm_list = list_vms_on_esxi(host, username, password)

        # If AJAX request, store vm_list in session and return JSON with redirect
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            session['last_vm_list'] = vm_list
            session['last_vm_host'] = host
            session['authenticated'] = True
            return jsonify(success=True, message=message, redirect_url=url_for('main.vm_list_get'))

        # Non-AJAX: store in session and render template
        session['authenticated'] = True
        flash(message, "success")
    except VmwareConnectionError as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, message=str(e)), 400
        flash(str(e), "error")
        return redirect(url_for("main.source_details"))

    # Store a small representation in session for the selection step.
    # For production, use a DB or cache store (Redis) and do not store secrets in session.
    session["last_vm_list"] = vm_list
    return render_template("vm_list.html", vms=vm_list, host=host)


@bp.route('/vm-list', methods=['GET'])
def vm_list_get():
    """Render VM list from session data (used after AJAX connect)."""
    vms = session.get('last_vm_list')
    host = session.get('last_vm_host')
    if vms is None:
        flash('No VM list found in session. Please connect first.', 'error')
        return redirect(url_for('main.source_details'))

    auth_flag = session.pop('authenticated', False)
    return render_template('vm_list.html', vms=vms, host=host, authenticated=auth_flag)


@bp.route("/start-migration", methods=["POST"])
def start_migration():
    """Receive selected VM serial numbers and show migration page for those VMs.
    
    Supports formats:
    - Single: "1"
    - Multiple: "1,3,5"
    - Range: "5-7"
    - Mixed: "1,3,5-7"
    """
    vms = session.get('last_vm_list')
    if not vms:
        flash("No VM list found in session. Please connect first.", "error")
        return redirect(url_for("main.index"))

    serial_input = request.form.get("selected_vm", "").strip()
    if not serial_input:
        flash("Please enter at least one VM serial number.", "error")
        return redirect(url_for("main.vm_list_get"))

    # Parse the input to extract all serial numbers
    selected_indices = set()
    try:
        parts = serial_input.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Handle range (e.g., "5-7")
                range_parts = part.split('-')
                if len(range_parts) != 2:
                    raise ValueError(f"Invalid range format: {part}")
                start = int(range_parts[0].strip())
                end = int(range_parts[1].strip())
                if start > end:
                    start, end = end, start
                for i in range(start, end + 1):
                    selected_indices.add(i)
            else:
                # Handle single number
                num = int(part)
                selected_indices.add(num)
    except ValueError as e:
        flash(f"Invalid input format: {str(e)}. Use format like '1' or '1,3,5-7'.", "error")
        return redirect(url_for("main.vm_list_get"))

    # Validate all indices are within range
    invalid_indices = [i for i in selected_indices if i < 1 or i > len(vms)]
    if invalid_indices:
        flash(f"Invalid serial numbers: {', '.join(map(str, sorted(invalid_indices)))}. Valid range is 1-{len(vms)}.", "error")
        return redirect(url_for("main.vm_list_get"))

    # Get the selected VMs in order
    selected_vms = [vms[i - 1] for i in sorted(selected_indices)]
    
    # ✓ UPDATE SELECTED VM SERIAL NUMBERS in the migration script
    if update_selected_vms:
        # Pass only the serial numbers (sorted)
        serial_numbers = sorted(list(selected_indices))
        update_selected_vms(serial_numbers)
        print(f"[INFO] Selected VM serial numbers updated in script: {serial_numbers}")
    
    return render_template("migration_started.html", vms=selected_vms)

@bp.route('/select-vm', methods=['POST'])
def select_vm():
    """AJAX endpoint: update selected VM serial (single) in config.json.

    Accepts JSON { serial: "3" } or form data 'serial' / 'selected_vm'.
    """
    vms = session.get('last_vm_list')
    if not vms:
        return jsonify(success=False, message='No VM list in session'), 400

    serial = None
    if request.is_json:
        body = request.get_json(silent=True) or {}
        serial = body.get('serial')
    else:
        serial = request.form.get('serial') or request.form.get('selected_vm')

    try:
        serial_num = int(str(serial).strip())
    except Exception:
        return jsonify(success=False, message='Invalid serial number'), 400

    if serial_num < 1 or serial_num > len(vms):
        return jsonify(success=False, message=f'Invalid serial number. Valid range 1-{len(vms)}'), 400

    # Update config via migration helper
    if update_selected_vms:
        try:
            update_selected_vms([serial_num])
        except Exception as e:
            return jsonify(success=False, message=f'Failed to update config: {e}'), 500
        return jsonify(success=True, message='Selection saved', serial=serial_num)

    return jsonify(success=False, message='Update function not available'), 500

@bp.route("/destination-details", methods=["GET"])
def destination_details():
    """Show destination connection form based on user's platform choice."""
    platforms = session.get("platforms")
    if not platforms:
        return redirect(url_for("main.index"))
    
    destination = platforms["destination"]
    return render_template("destination_details.html", destination=destination)


@bp.route("/connect-destination", methods=["POST"])
def connect_destination():
    """Attempt to connect to the destination Proxmox platform using password authentication."""
    import sys
    
    print(f"[ROUTE] /connect-destination called", file=sys.stderr)
    
    platforms = session.get("platforms")
    if not platforms:
        print(f"[ROUTE] No platforms in session", file=sys.stderr)
        return redirect(url_for("main.index"))

    destination = platforms["destination"]
    if destination != "proxmox":
        msg = "Only Proxmox destination is implemented."
        print(f"[ROUTE] Wrong destination: {destination}", file=sys.stderr)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, message=msg), 400
        flash(msg, "error")
        return redirect(url_for("main.destination_details"))

    # Get form data
    host = request.form.get("host", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    port = request.form.get("port", "8006").strip()

    print(f"[ROUTE] Form data - host={host}, username={username}, port={port}", file=sys.stderr)

    # Validate inputs
    if not host or not username or not password:
        msg = "Provide host, username, and password to connect."
        print(f"[ROUTE] Missing inputs", file=sys.stderr)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, message=msg), 400
        flash(msg, "error")
        return redirect(url_for("main.destination_details"))

    try:
        port = int(port)
    except ValueError:
        port = 8006

    # Try to verify Proxmox credentials using password
    try:
        if not verify_proxmox_credentials:
            msg = "Proxmox client not available."
            print(f"[ROUTE] ERROR: {msg}", file=sys.stderr)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, message=msg), 500
            flash(msg, "error")
            return redirect(url_for("main.destination_details"))

        print(f"[ROUTE] Verifying credentials for {host}:{port}", file=sys.stderr)
        
        success, message = verify_proxmox_credentials(host, username, password, port)
        print(f"[ROUTE] Verification result - success={success}, message={message}", file=sys.stderr)
        
        if not success:
            print(f"[ROUTE] Authentication failed: {message}", file=sys.stderr)
            # If AJAX request, return JSON error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                resp = jsonify(success=False, message=message)
                print(f"[ROUTE] Returning error JSON: {resp.get_json()}", file=sys.stderr)
                return resp, 400
            flash(message, "error")
            return redirect(url_for("main.destination_details"))

        # ✓ AUTHENTICATION SUCCESSFUL - Store Proxmox credentials in session
        session['destination_host'] = host
        session['destination_user'] = username
        session['destination_pass'] = password
        session['destination_port'] = port
        session['authenticated_destination'] = True
        session.modified = True  # Force session update
        print(f"[ROUTE] Authentication successful - stored in session", file=sys.stderr)

        # If AJAX request, return JSON with redirect
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            resp = jsonify(
                success=True,
                message=message,
                redirect_url=url_for('main.migration_summary')
            )
            print(f"[ROUTE] Returning success JSON", file=sys.stderr)
            return resp

        flash(message, "success")

    except Exception as e:
        print(f"[ROUTE] EXCEPTION: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            resp = jsonify(success=False, message=f"Connection failed: {str(e)}")
            print(f"[ROUTE] Returning exception JSON", file=sys.stderr)
            return resp, 500
        flash(f"Connection failed: {str(e)}", "error")
        return redirect(url_for("main.destination_details"))

    return redirect(url_for("main.migration_summary"))


@bp.route("/migration-summary", methods=["GET"])
def migration_summary():
    """Show migration summary with both source and destination details."""
    # Check if we have all required information
    source_vms = session.get('last_vm_list')
    dest_host = session.get('destination_host')
    
    if not source_vms or not dest_host:
        flash("Missing required information. Please start from the beginning.", "error")
        return redirect(url_for("main.index"))

    auth_flag = session.pop('authenticated_destination', False)
    
    return render_template(
        'migration_summary.html',
        source_vms=source_vms,
        destination_host=dest_host,
        authenticated=auth_flag
    )


@bp.route('/start-remote-migration', methods=['POST'])
def start_remote_migration_route():
    """Start remote migration by uploading and running the script via SSH.

    This reads Proxmox SSH creds from session (destination_host, destination_user, destination_pass)
    and starts a background job. Returns a job id for polling.
    """
    host = session.get('destination_host')
    user = session.get('destination_user')
    password = session.get('destination_pass')
    port = session.get('destination_port', 22)

    if not host or not user or not password:
        return jsonify(success=False, message='Missing destination SSH credentials. Connect first.'), 400

    try:
        job_id = start_remote_migration(host, user, password, port=int(port), remote_path='/root')
        return jsonify(success=True, job_id=job_id)
    except SSHRunnerError as e:
        return jsonify(success=False, message=str(e)), 500
    except Exception as e:
        return jsonify(success=False, message=f'Failed to start remote migration: {e}'), 500


@bp.route('/migration-status/<job_id>', methods=['GET'])
def migration_status(job_id):
    try:
        job = get_job_status(job_id)
        return jsonify(success=True, job=job)
    except SSHRunnerError:
        return jsonify(success=False, message='Job not found'), 404
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500

