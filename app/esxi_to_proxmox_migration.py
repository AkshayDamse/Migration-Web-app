import os
import subprocess
import shutil
import json

# ============================================================================
# CONFIGURATION PATH - Customize this for your system
# ============================================================================
# Change this path to the location of config.json on your system
# Examples:
#   Windows: r"C:\path\to\config.json"
#   Linux/Mac: "/path/to/config.json"
#   Relative (from project root): os.path.join(os.path.dirname(__file__), "config.json")
# 
# IMPORTANT: Update this path if running on a different system!
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

# ============================================================================
# DEFAULT CONFIGURATION
# ============================================================================
DEFAULT_CONFIG = {
    "esxi_host": "192.168.203.74",
    "esxi_user": "root",
    "esxi_pass": "India@123",
    "storage": "local-lvm",
    "export_root": "./exports",
    "ovftool": "ovftool",
    "selected_vms": []
}


def _load_config():
    """Load configuration from JSON file. Return default if not found."""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
    except Exception as e:
        print(f"[WARNING] Could not load config from {CONFIG_PATH}: {e}")
    return DEFAULT_CONFIG.copy()


def _save_config(config):
    """Save configuration to JSON file."""
    try:
        tmp_path = CONFIG_PATH + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, CONFIG_PATH)
        return True
    except Exception as e:
        print(f"[ERROR] Could not save config to {CONFIG_PATH}: {e}")
        return False


# Load current configuration from file
_current_config = _load_config()

# Expose config values as module-level variables (for backward compatibility)
ESXI_HOST = _current_config.get('esxi_host', DEFAULT_CONFIG['esxi_host'])
ESXI_USER = _current_config.get('esxi_user', DEFAULT_CONFIG['esxi_user'])
ESXI_PASS = _current_config.get('esxi_pass', DEFAULT_CONFIG['esxi_pass'])
STORAGE = _current_config.get('storage', DEFAULT_CONFIG['storage'])
EXPORT_ROOT = _current_config.get('export_root', DEFAULT_CONFIG['export_root'])
OVFTOOL = _current_config.get('ovftool', DEFAULT_CONFIG['ovftool'])
sel = _current_config.get('selected_vms', DEFAULT_CONFIG['selected_vms'])


# ============================================================================
# LOAD FUNCTION (call at runtime to get fresh config)
# ============================================================================
def load_config():
    """Reload configuration from disk (call before using config values)."""
    global ESXI_HOST, ESXI_USER, ESXI_PASS, STORAGE, EXPORT_ROOT, OVFTOOL, sel, _current_config
    _current_config = _load_config()
    ESXI_HOST = _current_config.get('esxi_host', DEFAULT_CONFIG['esxi_host'])
    ESXI_USER = _current_config.get('esxi_user', DEFAULT_CONFIG['esxi_user'])
    ESXI_PASS = _current_config.get('esxi_pass', DEFAULT_CONFIG['esxi_pass'])
    STORAGE = _current_config.get('storage', DEFAULT_CONFIG['storage'])
    EXPORT_ROOT = _current_config.get('export_root', DEFAULT_CONFIG['export_root'])
    OVFTOOL = _current_config.get('ovftool', DEFAULT_CONFIG['ovftool'])
    sel = _current_config.get('selected_vms', DEFAULT_CONFIG['selected_vms'])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def update_esxi_config(host, user, password):
    """
    Update ESXi configuration in config.json after successful authentication.
    
    Args:
        host (str): ESXi host IP/hostname
        user (str): ESXi username
        password (str): ESXi password
    
    Returns:
        bool: True if update successful, False otherwise
    """
    try:
        # Read the current config from file
        config = _load_config()
        
        # Update ESXi configuration
        config['esxi_host'] = host
        config['esxi_user'] = user
        config['esxi_pass'] = password
        
        # Save to config file
        if not _save_config(config):
            return False

        # Update the in-memory variables so running process sees changes
        globals()['ESXI_HOST'] = host
        globals()['ESXI_USER'] = user
        globals()['ESXI_PASS'] = password
        
        print(f"✓ ESXi configuration updated successfully:")
        print(f"  Host: {host}")
        print(f"  User: {user}")
        print(f"  Config saved to: {CONFIG_PATH}")
        return True
        
    except Exception as e:
        print(f"✗ Error updating ESXi configuration: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_selected_vms(selected_serial_numbers):
    """
    Update the 'selected_vms' in config.json with selected VM serial numbers.
    
    Args:
        selected_serial_numbers (list): List of selected VM serial numbers (e.g., [1, 3, 5])
    
    Returns:
        bool: True if update successful, False otherwise
    """
    try:
        # Read the current config from file
        config = _load_config()
        
        # Update selected VMs in config
        sel_value = str(selected_serial_numbers)
        config['selected_vms'] = selected_serial_numbers

        # Save to config file
        if not _save_config(config):
            return False
        
        # Update the in-memory variable
        globals()['sel'] = selected_serial_numbers
        
        print(f"✓ Selected VM serial numbers updated successfully:")
        print(f"  sel = {selected_serial_numbers}")
        print(f"  Config saved to: {CONFIG_PATH}")
        return True
        
    except Exception as e:
        print(f"✗ Error updating selected VMs: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# MIGRATION LOGIC (to be extended)
# ============================================================================


