"""
Proxmox connection handler for verifying credentials and connecting to Proxmox hosts.
"""
import os
import ssl
import warnings
import socket

try:
    # Optional: proxmoxer library for Proxmox API
    from proxmoxer import ProxmoxAPI
    ProxmoxAPI_available = True
except ImportError:
    ProxmoxAPI = None
    ProxmoxAPI_available = False

# Check for requests library which proxmoxer often requires as a backend
try:
    import requests  # noqa: F401
    requests_available = True
except Exception:
    requests_available = False

# Disable all warnings
warnings.filterwarnings('ignore')

# Disable SSL certificate verification globally for development
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except:
    pass


class ProxmoxConnectionError(Exception):
    """Custom exception for Proxmox connection errors."""
    pass


def verify_proxmox_credentials(host: str, username: str, password: str, port: int = 8006) -> tuple[bool, str]:
    """
    Verify Proxmox credentials using password authentication.
    No SSL checks - bypasses all SSL/certificate validation.
    
    Args:
        host: Proxmox host IP or hostname
        username: Username (e.g., root@pam)
        password: Password for the user
        port: Proxmox API port (default 8006)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if not ProxmoxAPI_available:
        return False, "proxmoxer is not installed. Run: pip install proxmoxer"

    if not requests_available:
        # Give an explicit actionable error so the user knows what's missing
        return False, "The 'requests' Python package is required by proxmoxer. Run: pip install requests"
    
    try:
        import sys
        print(f"[PROXMOX] Attempting connection to {host}:{port}", file=sys.stderr)
        # Quick TCP check to fail fast if host/port are unreachable
        try:
            sock_timeout = 5
            sock = socket.create_connection((host, int(port)), timeout=sock_timeout)
            sock.close()
            print(f"[PROXMOX] TCP connect to {host}:{port} succeeded (timeout {sock_timeout}s)", file=sys.stderr)
        except Exception as sock_err:
            # Return a clear, actionable error for unreachable host/port
            msg = (
                f"Connection failed: cannot reach {host}:{port} (TCP connect failed: {sock_err}). "
                "Check IP, port, firewall, and network routing. Try: `ping {host}` and `Test-NetConnection -ComputerName {host} -Port {port}`"
            )
            print(f"[PROXMOX] TCP connect failed: {sock_err}", file=sys.stderr)
            return False, msg
        
        # Ensure SSL bypass is set
        ssl._create_default_https_context = ssl._create_unverified_context
        
        # Simple connection attempt - no SSL verification
        # Increase timeout to allow slower responses on some networks
        proxmox = ProxmoxAPI(
            host,
            user=username,
            password=password,
            port=int(port),
            verify_ssl=False,
            timeout=30
        )
        
        print(f"[PROXMOX] Connection created, attempting to get version", file=sys.stderr)
        
        # Test connection by getting version
        try:
            version_info = proxmox.version.get()
            version = version_info.get('version', 'unknown') if version_info else 'unknown'
            msg = f"Connected to Proxmox {version} at {host}:{port}"
            print(f"[PROXMOX] SUCCESS: {msg}", file=sys.stderr)
            return True, msg
        except Exception as version_err:
            # Even if version fails, connection might have succeeded
            print(f"[PROXMOX] Version check failed but connection OK: {str(version_err)}", file=sys.stderr)
            return True, f"Connected to Proxmox at {host}:{port}"
    
    except Exception as e:
        error_str = str(e)
        # Provide more guidance for timeout-like errors
        if 'Max retries exceeded' in error_str or 'timed out' in error_str or 'ConnectTimeout' in error_str:
            error_str = (
                error_str +
                " -- Network connection timed out while contacting Proxmox API. Check host/port and firewall. "
                "If the Proxmox web UI is reachable from this machine, ensure the API port (default 8006) is open."
            )
        print(f"[PROXMOX] FAILED: {error_str}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False, f"Connection failed: {error_str}"


def get_proxmox_nodes(host: str, username: str, password: str, port: int = 8006) -> list:
    """
    Get list of Proxmox nodes using password authentication.
    
    Args:
        host: Proxmox host IP or hostname
        username: Username (e.g., root@pam)
        password: Password for the user
        port: Proxmox API port (default 8006)
    
    Returns:
        list: List of nodes available in Proxmox cluster
        
    Raises:
        ProxmoxConnectionError on failures
    """
    if not ProxmoxAPI_available:
        raise ProxmoxConnectionError("proxmoxer is not installed.")
    
    try:
        # Simple connection - no SSL verification
        proxmox = ProxmoxAPI(
            host,
            user=username,
            password=password,
            port=port,
            verify_ssl=False
        )
        
        # Get list of nodes
        nodes = proxmox.nodes.get()
        return nodes
    
    except Exception as e:
        raise ProxmoxConnectionError(f"Unable to connect to Proxmox host {host}: {e}")


def get_proxmox_vms(host: str, username: str, password: str, port: int = 8006, node: str = None) -> list:
    """
    Get list of VMs (QEMU) from Proxmox using password authentication.
    
    Args:
        host: Proxmox host IP or hostname
        username: Username (e.g., root@pam)
        password: Password for the user
        port: Proxmox API port (default 8006)
        node: Specific node to query (if None, uses first available node)
    
    Returns:
        list: List of VM dictionaries with details
        
    Raises:
        ProxmoxConnectionError on failures
    """
    if not ProxmoxAPI_available:
        raise ProxmoxConnectionError("proxmoxer is not installed.")
    
    try:
        # Simple connection - no SSL verification
        proxmox = ProxmoxAPI(
            host,
            user=username,
            password=password,
            port=port,
            verify_ssl=False
        )
        
        # Get nodes if not specified
        if not node:
            nodes = proxmox.nodes.get()
            if not nodes:
                raise ProxmoxConnectionError("No nodes found in Proxmox cluster")
            node = nodes[0]['node']
        
        # Get QEMU VMs
        vms = proxmox.nodes(node).qemu.get()
        
        # Enrich VM data with config details
        enriched_vms = []
        for vm in vms:
            vm_id = vm['vmid']
            try:
                config = proxmox.nodes(node).qemu(vm_id).config.get()
                vm['config'] = config
                
                # Extract useful parameters
                vm['cpu'] = config.get('cores', 0) * config.get('sockets', 1)  # Total CPUs
                vm['memory'] = int(config.get('memory', 0))  # RAM in MB
                
                # Storage: parse disk sizes
                storage_info = {}
                for key, value in config.items():
                    if key.startswith('scsi') or key.startswith('virtio') or key.startswith('ide') or key.startswith('sata'):
                        # Parse disk size, e.g., "local:100" or "local:100,format=qcow2"
                        if ':' in str(value):
                            parts = str(value).split(',')
                            size_part = parts[0].split(':')
                            if len(size_part) > 1:
                                try:
                                    size_gb = float(size_part[1])
                                    storage_info[key] = size_gb
                                except ValueError:
                                    pass
                
                vm['storage'] = storage_info
                vm['total_storage_gb'] = sum(storage_info.values())
                
                # Network
                network_info = []
                for key, value in config.items():
                    if key.startswith('net'):
                        network_info.append(key)  # Just add the interface names
                vm['network'] = network_info
                
                # SCSI controller
                scsi_controller = config.get('scsihw', 'none')
                vm['scsi_controller'] = scsi_controller
                
            except Exception as e:
                print(f"Warning: Could not get config for VM {vm_id}: {e}")
                vm['config'] = {}
                vm['cpu'] = 0
                vm['memory'] = 0
                vm['storage'] = {}
                vm['total_storage_gb'] = 0
                vm['network'] = []
                vm['scsi_controller'] = 'none'
            
            enriched_vms.append(vm)
        
        return enriched_vms
    
    except Exception as e:
        raise ProxmoxConnectionError(f"Unable to get VMs from Proxmox host {host}: {e}")