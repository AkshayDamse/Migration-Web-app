"""
Proxmox connection handler for verifying credentials and connecting to Proxmox hosts.
"""
import os

try:
    # Optional: proxmoxer library for Proxmox API
    from proxmoxer import ProxmoxAPI
    ProxmoxAPI_available = True
except ImportError:
    ProxmoxAPI = None
    ProxmoxAPI_available = False


class ProxmoxConnectionError(Exception):
    """Custom exception for Proxmox connection errors."""
    pass


def verify_proxmox_credentials(host: str, username: str, password: str, port: int = 8006) -> tuple[bool, str]:
    """
    Verify Proxmox credentials by attempting a connection.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if not ProxmoxAPI_available:
        if os.getenv("PROXMOX_BYPASS", "0") == "1":
            return True, "Development mode: Proxmox authentication bypassed"
        return False, "proxmoxer is not installed. Install proxmoxer to use Proxmox features."
    
    try:
        # Attempt to connect to Proxmox API
        # Disable SSL verification for development
        proxmox = ProxmoxAPI(
            host,
            user=username,
            password=password,
            port=port,
            verify_ssl=False
        )
        
        # Test the connection by getting the version
        version = proxmox.version.get()
        
        return True, f"Authentication successful - Proxmox {version.get('version', 'unknown')}"
    
    except Exception as e:
        error_msg = str(e).lower()
        
        if "invalid credentials" in error_msg or "unauthorized" in error_msg:
            return False, "Invalid username or password"
        elif "connection refused" in error_msg or "cannot connect" in error_msg:
            return False, f"Could not connect to host {host}:{port}. Please verify the hostname/IP and port."
        elif "certificate" in error_msg or "ssl" in error_msg:
            return False, f"SSL certificate error: {str(e)}"
        else:
            return False, f"Connection failed: {str(e)}"


def get_proxmox_nodes(host: str, username: str, password: str, port: int = 8006) -> list:
    """
    Get list of Proxmox nodes after successful authentication.
    
    Returns:
        list: List of node names available in Proxmox cluster
        
    Raises:
        ProxmoxConnectionError on failures
    """
    if not ProxmoxAPI_available:
        if os.getenv("PROXMOX_BYPASS", "0") == "1":
            return [{"node": "test-node", "status": "online"}]
        raise ProxmoxConnectionError("proxmoxer is not installed.")
    
    try:
        # Disable SSL verification for development
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
