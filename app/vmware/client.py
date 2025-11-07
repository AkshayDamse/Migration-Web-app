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
import os

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


def verify_credentials(host: str, username: str, password: str, port: int = 443) -> tuple[bool, str]:
    """Verify ESXi credentials without listing VMs.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if SmartConnect is None:
        if os.getenv("VMWARE_BYPASS_PYVMOMI", "0") == "1":
            return True, "Development mode: Authentication bypassed"
        return False, "pyvmomi is not installed"
        
    si = None
    try:
        # Completely disable SSL verification
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        
        si = SmartConnect(
            host=host,
            user=username,
            pwd=password,
            port=port,
            disableSslCertValidation=True  # Explicitly disable SSL validation
        )
        return True, "Authentication successful"
    except Exception as e:
        error_msg = str(e)
        if "incorrect user name" in error_msg.lower() or "invalid credentials" in error_msg.lower():
            return False, "Invalid username or password"
        elif "connection refused" in error_msg.lower():
            return False, f"Could not connect to host {host}. Please verify the hostname/IP and port."
        else:
            return False, f"Connection failed: {str(e)}"
    finally:
        if si:
            try:
                Disconnect(si)
            except Exception:
                pass

def list_vms_on_esxi(host: str, username: str, password: str, port: int = 443) -> List[Dict]:
    """Connect to an ESXi host and list virtual machines.

    Returns a list of dicts: {"name": str, "instance_uuid": str}

    Raises:
        VmwareConnectionError on failures
    """
    bypass = os.getenv("VMWARE_BYPASS_PYVMOMI", "0") == "1"

    if SmartConnect is None:
        if bypass:
            return [
                {"name": "(dev) sample-vm-1", "instance_uuid": "dev-uuid-1"},
                {"name": "(dev) sample-vm-2", "instance_uuid": "dev-uuid-2"},
            ]
        raise VmwareConnectionError("pyvmomi is not installed. Install pyvmomi to use ESXi features.")
        
    # First verify credentials (verify_credentials returns (ok, message))
    ok, msg = verify_credentials(host, username, password, port)
    if not ok:
        raise VmwareConnectionError(msg)

    si = None
    try:
        # Disable certificate verification globally for this connection
        # by using an unverified default HTTPS context. This avoids the
        # "Cannot set verify_mode to CERT_NONE when check_hostname is enabled"
        # error that can occur when manipulating SSLContext attributes in the
        # wrong order on some Python versions.
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
        except Exception:
            # If this fails, continue and let SmartConnect raise a clear error
            pass

        # Call SmartConnect directly; pyvmomi will use the default context
        si = SmartConnect(host=host, user=username, pwd=password, port=port)
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
