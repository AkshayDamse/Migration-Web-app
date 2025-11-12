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
        
        # Ensure SSL bypass is set
        ssl._create_default_https_context = ssl._create_unverified_context
        
        # Simple connection attempt - no SSL verification
        proxmox = ProxmoxAPI(
            host,
            user=username,
            password=password,
            port=int(port),
            verify_ssl=False,
            timeout=10
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
