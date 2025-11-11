import os
import subprocess
import shutil

# ============================================================================
# CONFIGURATION - ESXi
# ============================================================================
# These variables are automatically updated after successful authentication
# Do not manually edit unless you know what you're doing

ESXI_HOST = "192.168.203.74"
ESXI_USER = "root"
ESXI_PASS = "India@123"
STORAGE = "local-lvm"
EXPORT_ROOT = "./exports"
OVFTOOL = "ovftool"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def update_esxi_config(host, user, password):
    """
    Update ESXi configuration in this script file after successful authentication.
    
    Args:
        host (str): ESXi host IP/hostname
        user (str): ESXi username
        password (str): ESXi password
    
    Returns:
        bool: True if update successful, False otherwise
    """
    try:
        # Read the current script file
        script_path = __file__
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Replace the configuration variables
        # Using simple string replacement for clarity
        content = content.replace(
            f'ESXI_HOST = "{globals().get("ESXI_HOST", "")}"',
            f'ESXI_HOST = "{host}"'
        )
        content = content.replace(
            f'ESXI_USER = "{globals().get("ESXI_USER", "")}"',
            f'ESXI_USER = "{user}"'
        )
        content = content.replace(
            f'ESXI_PASS = "{globals().get("ESXI_PASS", "")}"',
            f'ESXI_PASS = "{password}"'
        )
        
        # Write back to the script file
        with open(script_path, 'w') as f:
            f.write(content)
        
        # Update the in-memory variables
        globals()['ESXI_HOST'] = host
        globals()['ESXI_USER'] = user
        globals()['ESXI_PASS'] = password
        
        print(f"✓ ESXi configuration updated successfully:")
        print(f"  Host: {host}")
        print(f"  User: {user}")
        return True
        
    except Exception as e:
        print(f"✗ Error updating ESXi configuration: {e}")
        return False


# ============================================================================
# MIGRATION LOGIC (to be extended)
# ============================================================================


