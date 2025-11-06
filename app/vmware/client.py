"""
Lightweight pyvmomi wrapper to connect to an ESXi host and list VMs.

This module is intentionally small and focused. It demonstrates how to
connect to an ESXi server and return a JSON-serializable list of VMs with
their names and instance UUIDs (used here as a 'serial').

For production use:
- Add TLS verification and certificate management
- Use secure secret handling and avoid logging credentials
- Add robust exception handling and retries
"""
from typing import List, Dict

try:
    # pyvmomi imports
    from pyVim.connect import SmartConnect, Disconnect
    from pyVmomi import vim
    import ssl
except Exception:  # pragma: no cover - import may fail if not installed
    SmartConnect = None
    Disconnect = None
    vim = None


class VmwareConnectionError(Exception):
    pass


def list_vms_on_esxi(host: str, username: str, password: str, port: int = 443) -> List[Dict]:
    """Connect to an ESXi host and list virtual machines.

    Returns a list of dicts: {"name": str, "instance_uuid": str}

    Raises:
        VmwareConnectionError on failures
    """
    if SmartConnect is None:
        raise VmwareConnectionError("pyvmomi is not installed. Install pyvmomi to use ESXi features.")

    si = None
    try:
        # Create SSL context that doesn't verify certificates for dev/test
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.verify_mode = ssl.CERT_NONE
        
        si = SmartConnect(host=host, user=username, pwd=password, port=port, sslContext=context)
    except Exception as e:
        raise VmwareConnectionError(f"Unable to connect to ESXi host {host}: {e}")

    try:
        content = si.RetrieveContent()
        container = content.rootFolder  # start from the root
        view_type = [vim.VirtualMachine]
        recursive = True
        container_view = content.viewManager.CreateContainerView(container, view_type, recursive)
        vms = container_view.view

        vm_list = []
        for vm in vms:
            # instanceUuid is guaranteed for VMs (used here as a serial/identifier)
            instance_uuid = None
            try:
                instance_uuid = vm.config.instanceUuid
            except Exception:
                # Fallback to summary config uuid
                try:
                    instance_uuid = vm.summary.config.vmId
                except Exception:
                    instance_uuid = "unknown"

            vm_list.append({"name": vm.name, "instance_uuid": instance_uuid})

        # Clean up view
        container_view.Destroy()
        return vm_list
    finally:
        try:
            Disconnect(si)
        except Exception:
            pass
