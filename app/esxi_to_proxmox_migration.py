import os
import subprocess
import shutil
import json
from pathlib import Path

# ============================================================================
# CONFIGURATION SECTION
# ============================================================================
# These credentials are updated automatically by the web app after successful
# authentication. Do not manually edit these unless you know what you're doing.

CONFIG = {
    "esxi_host": "esxi.example.com",
    "esxi_user": "root",
    "esxi_password": "your_password",
    "proxmox_host": "proxmox.example.com",
    "proxmox_user": "root@pam",
    "proxmox_password": "your_proxmox_password",
}

# Path to store authenticated credentials (created by web app)
CONFIG_FILE = Path(__file__).parent / "config.json"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_config():
    """Load configuration from config.json if it exists, otherwise use defaults."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                loaded_config = json.load(f)
                CONFIG.update(loaded_config)
                print(f"✓ Configuration loaded from {CONFIG_FILE}")
        except Exception as e:
            print(f"⚠ Could not load config file: {e}")
    return CONFIG


def save_config(host, user, password, source="esxi"):
    """
    Save authenticated ESXi credentials to config.json.
    Only call this after successful authentication!
    
    Args:
        host (str): ESXi host IP/hostname
        user (str): ESXi username
        password (str): ESXi password
        source (str): Source platform ("esxi" or "proxmox")
    """
    try:
        # Load existing config or use defaults
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                saved_config = json.load(f)
        else:
            saved_config = CONFIG.copy()

        # Update only the relevant credentials
        if source == "esxi":
            saved_config['esxi_host'] = host
            saved_config['esxi_user'] = user
            saved_config['esxi_password'] = password
        elif source == "proxmox":
            saved_config['proxmox_host'] = host
            saved_config['proxmox_user'] = user
            saved_config['proxmox_password'] = password

        # Write to config file
        with open(CONFIG_FILE, 'w') as f:
            json.dump(saved_config, f, indent=2)

        # Update in-memory CONFIG as well
        CONFIG.update(saved_config)
        
        print(f"✓ Configuration updated for {source}: {host}")
        return True
    except Exception as e:
        print(f"✗ Error saving configuration: {e}")
        return False


def get_esxi_config():
    """Get current ESXi configuration."""
    load_config()
    return {
        "host": CONFIG.get("esxi_host"),
        "user": CONFIG.get("esxi_user"),
        "password": CONFIG.get("esxi_password"),
    }


def get_proxmox_config():
    """Get current Proxmox configuration."""
    load_config()
    return {
        "host": CONFIG.get("proxmox_host"),
        "user": CONFIG.get("proxmox_user"),
        "password": CONFIG.get("proxmox_password"),
    }


# ============================================================================
# MIGRATION LOGIC (to be extended)
# ============================================================================
