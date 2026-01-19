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
    from ..esxi_to_proxmox_migration import update_esxi_config, update_proxmox_config, update_selected_vms
except ImportError:
    update_esxi_config = None
    update_proxmox_config = None
    update_selected_vms = None

# Import KVM migration config updater
try:
    from ..kvm_migration import update_esxi_config as update_esxi_config_kvm, update_selected_vms as update_selected_vms_kvm, update_kvm_config
except ImportError:
    update_esxi_config_kvm = None
    update_selected_vms_kvm = None
    update_kvm_config = None

# Import Proxmox client (optional) and SSH runner
try:
    from ..proxmox.client import verify_proxmox_credentials, ProxmoxConnectionError
except ImportError:
    verify_proxmox_credentials = None
    ProxmoxConnectionError = None

# Import Proxmox SSH runner
try:
    from ..ssh_runner import start_remote_migration, get_job_status, SSHRunnerError
except ImportError:
    start_remote_migration = None
    get_job_status = None
    SSHRunnerError = None

# Import KVM SSH runner
try:
    from ..kssh_runner import start_kvm_migration, get_job_status as get_kvm_job_status, SSHRunnerError as KSSHRunnerError
except ImportError:
    start_kvm_migration = None
    get_kvm_job_status = None
    KSSHRunnerError = None

# Migration module (to read current selected_vms state)
try:
    from .. import esxi_to_proxmox_migration as migration_mod
except Exception:
    migration_mod = None

# KVM migration module
try:
    from .. import kvm_migration as kvm_migration_mod
except Exception:
    kvm_migration_mod = None

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
    selected_serials = []
    if migration_mod:
        try:
            migration_mod.load_config()
            selected_serials = migration_mod.sel if isinstance(migration_mod.sel, list) else []
        except Exception:
            selected_serials = []
    return render_template("vm_list.html", vms=vm_list, host=host, selected_serials=selected_serials)


@bp.route('/vm-list', methods=['GET'])
def vm_list_get():
    """Render VM list from session data (used after AJAX connect)."""
    vms = session.get('last_vm_list')
    host = session.get('last_vm_host')
    if vms is None:
        flash('No VM list found in session. Please connect first.', 'error')
        return redirect(url_for('main.source_details'))

    auth_flag = session.pop('authenticated', False)
    selected_serials = []
    if migration_mod:
        try:
            migration_mod.load_config()
            selected_serials = migration_mod.sel if isinstance(migration_mod.sel, list) else []
        except Exception:
            selected_serials = []
    return render_template('vm_list.html', vms=vms, host=host, authenticated=auth_flag, selected_serials=selected_serials)


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
    """Attempt to connect to the destination platform (Proxmox or KVM) using password authentication."""
    import sys
    
    print(f"[ROUTE] /connect-destination called", file=sys.stderr)
    
    platforms = session.get("platforms")
    if not platforms:
        print(f"[ROUTE] No platforms in session", file=sys.stderr)
        return redirect(url_for("main.index"))

    destination = platforms["destination"]
    print(f"[ROUTE] destination from platforms dict: {destination}", file=sys.stderr)
    
    if destination not in ["proxmox", "kvm"]:
        msg = "Only Proxmox and KVM destinations are supported."
        print(f"[ROUTE] Wrong destination: {destination}", file=sys.stderr)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, message=msg), 400
        flash(msg, "error")
        return redirect(url_for("main.destination_details"))

    # Get form data (SSH credentials for direct execution)
    host = request.form.get("host", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    port = request.form.get("port", "22").strip()

    print(f"[ROUTE] SSH Form data - host={host}, username={username}, port={port}, destination={destination}", file=sys.stderr)

    # Validate inputs
    if not host or not username or not password:
        msg = f"Provide host, username, and password for SSH to {destination}."
        print(f"[ROUTE] Missing inputs", file=sys.stderr)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, message=msg), 400
        flash(msg, "error")
        return redirect(url_for("main.destination_details"))

    try:
        port = int(port)
    except ValueError:
        port = 22

    # Store destination in session for later pages
    session['destination_host'] = host
    session['destination_user'] = username
    session['destination_pass'] = password
    session['destination_port'] = port
    session['destination_platform'] = destination  # Store destination platform separately
    session['authenticated_destination'] = True
    session.modified = True
    
    print(f"[ROUTE] After storing in /connect-destination:", file=sys.stderr)
    print(f"[ROUTE]   destination variable: {destination}", file=sys.stderr)
    print(f"[ROUTE]   session['destination_platform']: {session.get('destination_platform')}", file=sys.stderr)
    print(f"[ROUTE]   session.modified: {session.modified}", file=sys.stderr)
    print(f"[ROUTE]   Full session: {dict(session)}", file=sys.stderr)

    # ✓ UPDATE CONFIG based on destination platform
    if destination == "kvm":
        if update_kvm_config:
            update_kvm_config(host, username, password)
            print(f"[INFO] KVM configuration updated: {host}")
        
        # Use KVM runner if available
        if not start_kvm_migration:
            msg = 'KVM SSH runner not available (kssh_runner missing)'
            print(f"[ROUTE] KVM runner not available", file=sys.stderr)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, message=msg), 500
            flash(msg, 'error')
            return redirect(url_for('main.destination_details'))

        try:
            job_id = start_kvm_migration(host, username, password, port=int(port), remote_path='/root', local_script='app/kvm_migration.py', config_path='app/config.json')
        except KSSHRunnerError as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, message=str(e)), 500
            flash(str(e), 'error')
            return redirect(url_for('main.destination_details'))
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, message=f'Failed to start KVM migration: {e}'), 500
            flash(f'Failed to start KVM migration: {e}', 'error')
            return redirect(url_for('main.destination_details'))
    else:  # proxmox
        if update_proxmox_config:
            update_proxmox_config(host, username, password)
            print(f"[INFO] Proxmox destination configuration updated: {host}")
        
        # Use Proxmox runner
        if not start_remote_migration:
            msg = 'SSH runner not available (paramiko missing)'
            print(f"[ROUTE] Proxmox runner not available", file=sys.stderr)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, message=msg), 500
            flash(msg, 'error')
            return redirect(url_for('main.destination_details'))

        try:
            job_id = start_remote_migration(host, username, password, port=int(port), remote_path='/root', local_script='app/mscript.py', config_path='app/config.json')
        except SSHRunnerError as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, message=str(e)), 500
            flash(str(e), 'error')
            return redirect(url_for('main.destination_details'))
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, message=f'Failed to start Proxmox migration: {e}'), 500
            flash(f'Failed to start Proxmox migration: {e}', 'error')
            return redirect(url_for('main.destination_details'))

    # If AJAX, return JSON with redirect to migration summary with job_id
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(success=True, job_id=job_id, redirect_url=url_for('main.migration_summary') + f'?job_id={job_id}')

    # Non-AJAX: redirect to migration_summary with job_id
    return redirect(url_for('main.migration_summary', job_id=job_id))

@bp.route("/migration-summary", methods=["GET"])
def migration_summary():
    """Show migration summary with both source and destination details."""
    import sys
    
    print(f"[ROUTE] /migration-summary called", file=sys.stderr)
    print(f"[ROUTE] ALL session data: {dict(session)}", file=sys.stderr)
    
    # Check if we have all required information
    source_vms = session.get('last_vm_list')
    dest_host = session.get('destination_host')
    dest_platform_session = session.get('destination_platform')
    
    print(f"[ROUTE] source_vms: {source_vms is not None}", file=sys.stderr)
    print(f"[ROUTE] dest_host: {dest_host}", file=sys.stderr)
    print(f"[ROUTE] destination_platform from session: {dest_platform_session}", file=sys.stderr)
    
    if not source_vms or not dest_host:
        flash("Missing required information. Please start from the beginning.", "error")
        return redirect(url_for("main.index"))

    auth_flag = session.pop('authenticated_destination', False)
    
    # Use destination_platform from session (stored in /connect-destination)
    destination_platform = session.get('destination_platform', 'proxmox')
    print(f"[ROUTE] FINAL destination_platform being passed to template: {destination_platform}", file=sys.stderr)
    
    return render_template(
        'migration_summary.html',
        source_vms=source_vms,
        destination_host=dest_host,
        destination_platform=destination_platform,
        authenticated=auth_flag
    )


@bp.route('/start-remote-migration', methods=['POST'])
def start_remote_migration_route():
    """Start remote migration by uploading and running the script via SSH.

    This reads SSH creds from session (destination_host, destination_user, destination_pass)
    and starts a background job. Routes to the appropriate SSH runner based on destination platform.
    Returns a job id for polling.
    """
    import sys
    
    host = session.get('destination_host')
    user = session.get('destination_user')
    password = session.get('destination_pass')
    port = session.get('destination_port', 22)
    # Get destination platform from session (stored in /connect-destination)
    destination = session.get('destination_platform', 'proxmox')
    
    print(f"[ROUTE] /start-remote-migration - destination_platform from session: {destination}", file=sys.stderr)
    print(f"[ROUTE] Full session keys: {list(session.keys())}", file=sys.stderr)
    print(f"[ROUTE] destination_platform value: {session.get('destination_platform')}", file=sys.stderr)

    if not host or not user or not password:
        return jsonify(success=False, message='Missing destination SSH credentials. Connect first.'), 400

    try:
        # Route to appropriate SSH runner based on destination platform
        if destination == 'kvm':
            print(f"[ROUTE] Routing to KVM migration", file=sys.stderr)
            if not start_kvm_migration:
                return jsonify(success=False, message='KVM SSH runner not available'), 500
            job_id = start_kvm_migration(host, user, password, port=int(port), remote_path='/root', local_script='app/kvm_migration.py', config_path='app/config.json')
        else:  # proxmox
            print(f"[ROUTE] Routing to Proxmox migration", file=sys.stderr)
            if not start_remote_migration:
                return jsonify(success=False, message='Proxmox SSH runner not available'), 500
            job_id = start_remote_migration(host, user, password, port=int(port), remote_path='/root', local_script='app/mscript.py', config_path='app/config.json')
        return jsonify(success=True, job_id=job_id)
    except SSHRunnerError as e:
        return jsonify(success=False, message=str(e)), 500
    except KSSHRunnerError as e:
        return jsonify(success=False, message=str(e)), 500
    except Exception as e:
        return jsonify(success=False, message=f'Failed to start remote migration: {e}'), 500


@bp.route('/migration-status/<job_id>', methods=['GET'])
def migration_status(job_id):
    try:
        # Try Proxmox first
        try:
            job = get_job_status(job_id)
            return jsonify(success=True, job=job)
        except SSHRunnerError:
            # If not found in Proxmox, try KVM
            job = get_kvm_job_status(job_id)
            return jsonify(success=True, job=job)
    except SSHRunnerError:
        return jsonify(success=False, message='Job not found'), 404
    except KSSHRunnerError:
        return jsonify(success=False, message='Job not found'), 404
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500


@bp.route('/download-log/<job_id>', methods=['GET'])
def download_log(job_id):
    """Return the logs for a job as a downloadable text file."""
    try:
        job = get_job_status(job_id)
    except SSHRunnerError:
        flash('Job not found', 'error')
        return redirect(url_for('main.migration_summary'))

    logs = job.get('logs', [])
    content = '\n'.join(logs)
    from flask import Response
    filename = f'migration_{job_id}.log'
    headers = {
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Disposition': f'attachment; filename="{filename}"'
    }
    return Response(content, headers=headers)

