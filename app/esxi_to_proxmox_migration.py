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
sel = []


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
        
        # Replace the configuration variables using regex so updates work
        # regardless of the current in-file values.
        import re
        content = re.sub(r'^ESXI_HOST\s*=\s*".*"', f'ESXI_HOST = "{host}"', content, flags=re.MULTILINE)
        content = re.sub(r'^ESXI_USER\s*=\s*".*"', f'ESXI_USER = "{user}"', content, flags=re.MULTILINE)
        # For passwords allow any characters inside quotes (non-greedy)
        content = re.sub(r'^ESXI_PASS\s*=\s*".*"', f'ESXI_PASS = "{password}"', content, flags=re.MULTILINE)
        
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


def update_selected_vms(selected_serial_numbers):
    """
    Update the 'sel' variable with selected VM serial numbers.
    
    Args:
        selected_serial_numbers (list): List of selected VM serial numbers (e.g., [1, 3, 5])
    
    Returns:
        bool: True if update successful, False otherwise
    """
    try:
        # Read the current script file
        script_path = __file__
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Format the sel list as Python code with serial numbers
        sel_value = str(selected_serial_numbers)
        
        # Replace the sel variable using a robust regex that tolerates spaces
        import re
        content = re.sub(
            r'^sel\s*=\s*\[.*?\]',
            f'sel = {sel_value}',
            content,
            flags=re.DOTALL | re.MULTILINE
        )
        
        # Write back to the script file
        with open(script_path, 'w') as f:
            f.write(content)
        
        # Update the in-memory variable
        globals()['sel'] = selected_serial_numbers
        
        print(f"✓ Selected VM serial numbers updated successfully:")
        print(f"  sel = {selected_serial_numbers}")
        return True
        
    except Exception as e:
        print(f"✗ Error updating selected VMs: {e}")
        return False


# ============================================================================
# MIGRATION LOGIC (to be extended)
# ============================================================================


