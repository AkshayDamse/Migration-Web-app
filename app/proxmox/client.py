"""
Proxmox connection handler for verifying credentials and connecting to Proxmox hosts.
"""
import os
import ssl
import warnings

try:
    # Optional: proxmoxer library for Proxmox API
    from proxmoxer import ProxmoxAPI
    ProxmoxAPI_available = True
except ImportError:
    ProxmoxAPI = None
    ProxmoxAPI_available = False

# Disable all warnings
warnings.filterwarnings('ignore')

# Disable SSL certificate verification globally for development - set BEFORE any HTTPS connections
ssl._create_default_https_context = ssl._create_unverified_context


class ProxmoxConnectionError(Exception):
    """Custom exception for Proxmox connection errors."""
    pass


def verify_proxmox_credentials(host: str, username: str, password: str, port: int = 8006) -> tuple[bool, str]:
    """
    Verify Proxmox credentials by attempting a connection.
    No SSL checks - pure connection attempt.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if not ProxmoxAPI_available:
        return False, "proxmoxer is not installed. Install proxmoxer to use Proxmox features."
    
    try:
        # Simple connection attempt - no SSL verification
        proxmox = ProxmoxAPI(
            host,
            user=username,
            password=password,
            port=port,
            verify_ssl=False
        )
        
        # Test connection - just verify we can reach the API
        try:
            version_info = proxmox.version.get()
            version = version_info.get('version', 'unknown') if version_info else 'unknown'
        except:
            # Even if version fails, connection succeeded
            version = 'unknown'
        
        return True, f"Connected to Proxmox at {host}:{port}"
    
    except Exception as e:
        error_str = str(e)
        return False, f"Connection failed: {error_str}"


def get_proxmox_nodes(host: str, username: str, password: str, port: int = 8006) -> list:
    """
    Get list of Proxmox nodes after successful authentication.
    
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
