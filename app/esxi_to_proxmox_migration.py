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
    "source": {
        "esxi_host": "192.168.203.74",
        "esxi_user": "root",
        "esxi_pass": "India@123"
    },
    "destination": {
        "proxmox_host": "",
        "proxmox_user": "",
        "proxmox_pass": "",
        "kvm_host": "",
        "kvm_user": "",
        "kvm_pass": "",
        "kvm_storage_pool": ""
    },
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
# Source (ESXi)
source = _current_config.get('source', DEFAULT_CONFIG['source'])
ESXI_HOST = source.get('esxi_host', DEFAULT_CONFIG['source']['esxi_host'])
ESXI_USER = source.get('esxi_user', DEFAULT_CONFIG['source']['esxi_user'])
ESXI_PASS = source.get('esxi_pass', DEFAULT_CONFIG['source']['esxi_pass'])

# Destination (Proxmox)
destination = _current_config.get('destination', DEFAULT_CONFIG['destination'])
PROXMOX_HOST = destination.get('proxmox_host', DEFAULT_CONFIG['destination']['proxmox_host'])
PROXMOX_USER = destination.get('proxmox_user', DEFAULT_CONFIG['destination']['proxmox_user'])
PROXMOX_PASS = destination.get('proxmox_pass', DEFAULT_CONFIG['destination']['proxmox_pass'])

# Other
STORAGE = _current_config.get('storage', DEFAULT_CONFIG['storage'])
EXPORT_ROOT = _current_config.get('export_root', DEFAULT_CONFIG['export_root'])
OVFTOOL = _current_config.get('ovftool', DEFAULT_CONFIG['ovftool'])
sel = _current_config.get('selected_vms', DEFAULT_CONFIG['selected_vms'])


# ============================================================================
# LOAD FUNCTION (call at runtime to get fresh config)
# ============================================================================
def load_config():
    """Reload configuration from disk (call before using config values)."""
    global ESXI_HOST, ESXI_USER, ESXI_PASS, PROXMOX_HOST, PROXMOX_USER, PROXMOX_PASS, STORAGE, EXPORT_ROOT, OVFTOOL, sel, _current_config, source, destination
    _current_config = _load_config()
    
    # Load source (ESXi) config
    source = _current_config.get('source', DEFAULT_CONFIG['source'])
    ESXI_HOST = source.get('esxi_host', DEFAULT_CONFIG['source']['esxi_host'])
    ESXI_USER = source.get('esxi_user', DEFAULT_CONFIG['source']['esxi_user'])
    ESXI_PASS = source.get('esxi_pass', DEFAULT_CONFIG['source']['esxi_pass'])
    
    # Load destination (Proxmox) config
    destination = _current_config.get('destination', DEFAULT_CONFIG['destination'])
    PROXMOX_HOST = destination.get('proxmox_host', DEFAULT_CONFIG['destination']['proxmox_host'])
    PROXMOX_USER = destination.get('proxmox_user', DEFAULT_CONFIG['destination']['proxmox_user'])
    PROXMOX_PASS = destination.get('proxmox_pass', DEFAULT_CONFIG['destination']['proxmox_pass'])
    
    # Load other config
    STORAGE = _current_config.get('storage', DEFAULT_CONFIG['storage'])
    EXPORT_ROOT = _current_config.get('export_root', DEFAULT_CONFIG['export_root'])
    OVFTOOL = _current_config.get('ovftool', DEFAULT_CONFIG['ovftool'])
    sel = _current_config.get('selected_vms', DEFAULT_CONFIG['selected_vms'])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def update_esxi_config(host, user, password):
    """
    Update ESXi source configuration in config.json after successful authentication.
    Updates ONLY the 'source' section. Does NOT touch 'destination' or 'selected_vms'.
    
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
        
        # Ensure source object exists
        if 'source' not in config:
            config['source'] = DEFAULT_CONFIG['source'].copy()
        
        # Update ESXi source configuration ONLY
        config['source']['esxi_host'] = host
        config['source']['esxi_user'] = user
        config['source']['esxi_pass'] = password
        
        # Save to config file
        if not _save_config(config):
            return False

        # Update the in-memory variables so running process sees changes
        globals()['ESXI_HOST'] = host
        globals()['ESXI_USER'] = user
        globals()['ESXI_PASS'] = password
        
        print(f"✓ ESXi source configuration updated successfully:")
        print(f"  Host: {host}")
        print(f"  User: {user}")
        print(f"  Config saved to: {CONFIG_PATH}")
        return True
        
    except Exception as e:
        print(f"✗ Error updating ESXi configuration: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_proxmox_config(host, user, password):
    """
    Update Proxmox destination configuration in config.json.
    Updates ONLY the 'destination.proxmox_*' fields. Does NOT touch 'source' or 'selected_vms'.
    
    Args:
        host (str): Proxmox host IP/hostname
        user (str): Proxmox username
        password (str): Proxmox password
    
    Returns:
        bool: True if update successful, False otherwise
    """
    try:
        # Read the current config from file
        config = _load_config()
        
        # Ensure destination object exists
        if 'destination' not in config:
            config['destination'] = DEFAULT_CONFIG['destination'].copy()
        
        # Update Proxmox destination configuration ONLY
        config['destination']['proxmox_host'] = host
        config['destination']['proxmox_user'] = user
        config['destination']['proxmox_pass'] = password
        
        # Save to config file
        if not _save_config(config):
            return False

        # Update the in-memory variables so running process sees changes
        globals()['PROXMOX_HOST'] = host
        globals()['PROXMOX_USER'] = user
        globals()['PROXMOX_PASS'] = password
        
        print(f"✓ Proxmox destination configuration updated successfully:")
        print(f"  Host: {host}")
        print(f"  User: {user}")
        print(f"  Config saved to: {CONFIG_PATH}")
        return True
        
    except Exception as e:
        print(f"✗ Error updating Proxmox destination configuration: {e}")
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


