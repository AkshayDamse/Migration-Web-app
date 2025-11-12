"""Test script to verify Proxmox connection."""
import sys
import ssl
import warnings

# Disable warnings
warnings.filterwarnings('ignore')
ssl._create_default_https_context = ssl._create_unverified_context

try:
    from proxmoxer import ProxmoxAPI
    print("[TEST] ProxmoxAPI imported successfully")
except Exception as e:
    print(f"[TEST] Failed to import ProxmoxAPI: {e}")
    sys.exit(1)

# Test with your credentials
HOST = "192.68.203.32"
USER = "root@pam"
PASSWORD = "password"  # Change this to your actual password
PORT = 8006

print(f"[TEST] Testing connection to {HOST}:{PORT}")
print(f"[TEST] User: {USER}")

try:
    proxmox = ProxmoxAPI(
        HOST,
        user=USER,
        password=PASSWORD,
        port=PORT,
        verify_ssl=False,
        timeout=10
    )
    print("[TEST] Connection successful!")
    
    # Try to get version
    try:
        version = proxmox.version.get()
        print(f"[TEST] Proxmox version: {version.get('version', 'unknown')}")
    except Exception as e:
        print(f"[TEST] Could not get version: {e}")
        print("[TEST] But connection was successful!")
    
except Exception as e:
    print(f"[TEST] Connection FAILED: {e}")
    import traceback
    traceback.print_exc()
