"""
KVM Migration Configuration Manager

Manages configuration for KVM destination hosts, similar to esxi_to_proxmox_migration.py
but specifically for KVM/libvirt environments.
"""
import os
import json

# ============================================================================
# CONFIGURATION PATH
# ============================================================================
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

# ============================================================================
# DEFAULT CONFIGURATION FOR KVM
# ============================================================================
DEFAULT_CONFIG = {
    "esxi_host": "192.168.203.74",
    "esxi_user": "root",
    "esxi_pass": "India@123",
    "kvm_host": "",
    "kvm_user": "",
    "kvm_pass": "",
    "kvm_storage_pool": "/var/lib/libvirt/images",
    "export_root": "./exports",
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
KVM_HOST = _current_config.get('kvm_host', DEFAULT_CONFIG['kvm_host'])
KVM_USER = _current_config.get('kvm_user', DEFAULT_CONFIG['kvm_user'])
KVM_PASS = _current_config.get('kvm_pass', DEFAULT_CONFIG['kvm_pass'])
KVM_STORAGE_POOL = _current_config.get('kvm_storage_pool', DEFAULT_CONFIG['kvm_storage_pool'])
EXPORT_ROOT = _current_config.get('export_root', DEFAULT_CONFIG['export_root'])
sel = _current_config.get('selected_vms', DEFAULT_CONFIG['selected_vms'])


# ============================================================================
# LOAD FUNCTION (call at runtime to get fresh config)
# ============================================================================
def load_config():
    """Reload configuration from disk (call before using config values)."""
    global ESXI_HOST, ESXI_USER, ESXI_PASS, KVM_HOST, KVM_USER, KVM_PASS, KVM_STORAGE_POOL, EXPORT_ROOT, sel, _current_config
    _current_config = _load_config()
    ESXI_HOST = _current_config.get('esxi_host', DEFAULT_CONFIG['esxi_host'])
    ESXI_USER = _current_config.get('esxi_user', DEFAULT_CONFIG['esxi_user'])
    ESXI_PASS = _current_config.get('esxi_pass', DEFAULT_CONFIG['esxi_pass'])
    KVM_HOST = _current_config.get('kvm_host', DEFAULT_CONFIG['kvm_host'])
    KVM_USER = _current_config.get('kvm_user', DEFAULT_CONFIG['kvm_user'])
    KVM_PASS = _current_config.get('kvm_pass', DEFAULT_CONFIG['kvm_pass'])
    KVM_STORAGE_POOL = _current_config.get('kvm_storage_pool', DEFAULT_CONFIG['kvm_storage_pool'])
    EXPORT_ROOT = _current_config.get('export_root', DEFAULT_CONFIG['export_root'])
    sel = _current_config.get('selected_vms', DEFAULT_CONFIG['selected_vms'])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def update_esxi_config(host, user, password):
    """
    Update ESXi source configuration in config.json.
    
    Args:
        host (str): ESXi host IP/hostname
        user (str): ESXi username
        password (str): ESXi password
    
    Returns:
        bool: True if successful, False otherwise
    """
    global ESXI_HOST, ESXI_USER, ESXI_PASS, _current_config
    _current_config = _load_config()
    _current_config['esxi_host'] = host
    _current_config['esxi_user'] = user
    _current_config['esxi_pass'] = password
    
    result = _save_config(_current_config)
    if result:
        ESXI_HOST = host
        ESXI_USER = user
        ESXI_PASS = password
    return result


def update_kvm_config(host, user, password, storage_pool=None):
    """
    Update KVM destination configuration in config.json.
    
    Args:
        host (str): KVM host IP/hostname
        user (str): KVM username
        password (str): KVM password
        storage_pool (str): Optional KVM storage pool path
    
    Returns:
        bool: True if successful, False otherwise
    """
    global KVM_HOST, KVM_USER, KVM_PASS, KVM_STORAGE_POOL, _current_config
    _current_config = _load_config()
    _current_config['kvm_host'] = host
    _current_config['kvm_user'] = user
    _current_config['kvm_pass'] = password
    if storage_pool:
        _current_config['kvm_storage_pool'] = storage_pool
    
    result = _save_config(_current_config)
    if result:
        KVM_HOST = host
        KVM_USER = user
        KVM_PASS = password
        if storage_pool:
            KVM_STORAGE_POOL = storage_pool
    return result


def update_selected_vms(serial_numbers):
    """
    Update the list of selected VM serial numbers in config.json.
    
    Args:
        serial_numbers (list): List of serial numbers to migrate
    
    Returns:
        bool: True if successful, False otherwise
    """
    global sel, _current_config
    _current_config = _load_config()
    _current_config['selected_vms'] = serial_numbers
    
    result = _save_config(_current_config)
    if result:
        sel = serial_numbers
    return result


# ============================================================================
# MIGRATION SCRIPT (placeholder for actual KVM migration logic)
# ============================================================================

def run_kvm_migration():
    """
    Run the KVM migration process using configuration from config.json.
    
    This is a placeholder - implement actual KVM-specific migration logic here.
    - Connect to ESXi, export VMs
    - Transfer to KVM host
    - Import to KVM/libvirt using virsh commands
    - Verify and start VMs
    """
    load_config()
    
    print("[KVM] Starting migration...")
    print(f"[KVM] ESXi Source: {ESXI_HOST}")
    print(f"[KVM] KVM Destination: {KVM_HOST}")
    print(f"[KVM] Selected VMs: {sel}")
    print(f"[KVM] Storage Pool: {KVM_STORAGE_POOL}")
    
    # TODO: Implement actual KVM migration logic
    # 1. Connect to ESXi and export selected VMs
    # 2. Transfer exported files to KVM host via SCP
    # 3. Import VMs into libvirt/KVM
    # 4. Configure network and storage
    # 5. Start VMs
    
    print("[KVM] Migration completed successfully!")


if __name__ == "__main__":
    run_kvm_migration()
