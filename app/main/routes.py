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
    """Receive selected VM serial number and show migration page for that VM only."""
    vms = session.get('last_vm_list')
    if not vms:
        flash("No VM list found in session. Please connect first.", "error")
        return redirect(url_for("main.index"))

    serial_str = request.form.get("selected_vm")
    try:
        serial = int(serial_str)
    except (TypeError, ValueError):
        flash("Please enter a valid serial number.", "error")
        return redirect(url_for("main.vm_list_get"))

    if serial < 1 or serial > len(vms):
        flash("Serial number out of range.", "error")
        return redirect(url_for("main.vm_list_get"))

    selected_vm = vms[serial - 1]
    return render_template("migration_started.html", vms=[selected_vm])
