# Migration Application - Complete Flow Documentation

## Overview
This document describes the complete migration flow with proper separation of concerns between source details, VM selection, and destination details in `config.json`.

---

## Architecture

### Config Structure
```json
{
  "source": {
    "esxi_host": "192.168.203.74",
    "esxi_user": "root",
    "esxi_pass": "password"
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
  "selected_vms": [],
  "storage": "local-lvm",
  "export_root": "./exports",
  "ovftool": "ovftool"
}
```

---

## Step-by-Step Flow

### STEP 1: Select Platforms
**Route:** `POST /select-platforms`

**What happens:**
- User chooses Source Platform (ESXi)
- User chooses Destination Platform (Proxmox or KVM)
- Platforms stored in Flask session

**Config Changes:** ❌ NONE
**Session Changes:** ✅ `session['platforms'] = {"source": "esxi", "destination": "proxmox" or "kvm"}`

**Next:** → STEP 2: Enter Source Details

---

### STEP 2: Enter Source Details
**Route:** `POST /connect-source`

**What happens:**
1. User enters ESXi host, username, password
2. Credentials verified via pyvmomi
3. VM list retrieved from ESXi
4. **Update config.json with source details**
5. Display VM list for selection

**Config Changes:** ✅ 
```python
update_source_esxi_details(host, username, password)
# Updates ONLY:
config['source']['esxi_host'] = host
config['source']['esxi_user'] = user
config['source']['esxi_pass'] = password
```

**Function Details:**
- **Location:** `app/esxi_to_proxmox_migration.py`
- **Name:** `update_source_esxi_details(host, user, password)`
- **Purpose:** Update source section without touching destination or selected_vms

**Session Changes:** ✅ `session['last_vm_list']` and `session['last_vm_host']`

**Next:** → STEP 3: Select VMs

---

### STEP 3: Select VMs
**Route:** `POST /start-migration`

**What happens:**
1. User enters VM serial numbers (supports: single, multiple, ranges)
   - Examples: "1", "1,3,5", "5-7", "1,3,5-7"
2. Input parsed and validated
3. **Update config.json with selected VMs**
4. Display migration summary

**Config Changes:** ✅ 
```python
update_selected_vm_list(serial_numbers)
# Updates ONLY:
config['selected_vms'] = [1, 3, 5, 6, 7]
```

**Function Details:**
- **Location:** `app/esxi_to_proxmox_migration.py`
- **Name:** `update_selected_vm_list(selected_serial_numbers)`
- **Purpose:** Update selected VMs without touching source or destination

**Session Changes:** None

**Next:** → STEP 4: Enter Destination Details

---

### STEP 4: Enter Destination Details
**Route:** `POST /connect-destination`

**What happens:**
1. User enters destination credentials (Proxmox or KVM)
2. Credentials verified via SSH
3. **Update config.json with destination details (based on platform)**
4. Start remote migration

**Config Changes:** ✅ (Platform-dependent)

#### If Destination = **KVM**:
```python
update_destination_kvm_details(host, username, password, storage_pool)
# Updates ONLY destination.kvm_*:
config['destination']['kvm_host'] = host
config['destination']['kvm_user'] = user
config['destination']['kvm_pass'] = password
config['destination']['kvm_storage_pool'] = storage_pool
```

**Function Details:**
- **Location:** `app/kvm_migration.py`
- **Name:** `update_destination_kvm_details(host, user, password, storage_pool=None)`
- **Purpose:** Update KVM destination without touching source or selected_vms

#### If Destination = **Proxmox**:
```python
update_destination_proxmox_details(host, username, password)
# Updates ONLY destination.proxmox_*:
config['destination']['proxmox_host'] = host
config['destination']['proxmox_user'] = user
config['destination']['proxmox_pass'] = password
```

**Function Details:**
- **Location:** `app/esxi_to_proxmox_migration.py`
- **Name:** `update_destination_proxmox_details(host, user, password)`
- **Purpose:** Update Proxmox destination without touching source or selected_vms

**Session Changes:** ✅ Destination credentials stored in session for SSH execution

**Next:** → Migration Started ✅

---

## Function Summary

### esxi_to_proxmox_migration.py

| Function | Purpose | Updates |
|----------|---------|---------|
| `update_source_esxi_details()` | Save ESXi source credentials | `config['source']` only |
| `update_destination_proxmox_details()` | Save Proxmox destination credentials | `config['destination'].proxmox_*` only |
| `update_selected_vm_list()` | Save selected VM serial numbers | `config['selected_vms']` only |

### kvm_migration.py

| Function | Purpose | Updates |
|----------|---------|---------|
| `update_esxi_config()` | Save ESXi source credentials (KVM workflow) | `config['source']` only |
| `update_destination_kvm_details()` | Save KVM destination credentials | `config['destination'].kvm_*` only |
| `update_selected_vms()` | Save selected VM serial numbers (KVM workflow) | `config['selected_vms']` only |

---

## Protection Mechanisms

### Each update function is isolated:
- ✅ Loads current config from disk
- ✅ Updates ONLY its specific section
- ✅ Saves back to disk
- ✅ Does NOT overwrite other sections

### Example Protection:
```python
# When updating source, destination remains unchanged
config = _load_config()
config['source']['esxi_host'] = new_host  # ← Only this changes
# config['destination'] and config['selected_vms'] remain unchanged
_save_config(config)
```

---

## Final Config State

After completing all 4 steps, config.json contains:

```json
{
  "source": {
    "esxi_host": "192.168.203.74",      // ← Updated in STEP 2
    "esxi_user": "root",                 // ← Updated in STEP 2
    "esxi_pass": "password"              // ← Updated in STEP 2
  },
  "destination": {
    "proxmox_host": "192.168.1.50",      // ← Updated in STEP 4 (if Proxmox)
    "proxmox_user": "root@pam",          // ← Updated in STEP 4 (if Proxmox)
    "proxmox_pass": "password",          // ← Updated in STEP 4 (if Proxmox)
    "kvm_host": "",                      // ← Empty if Proxmox chosen
    "kvm_user": "",                      // ← Empty if Proxmox chosen
    "kvm_pass": "",                      // ← Empty if Proxmox chosen
    "kvm_storage_pool": ""               // ← Empty if Proxmox chosen
  },
  "selected_vms": [1, 3, 5, 6, 7],      // ← Updated in STEP 3
  "storage": "local-lvm",
  "export_root": "./exports",
  "ovftool": "ovftool"
}
```

---

## Key Points

✅ **Source details stay intact** - Never overwritten by destination updates
✅ **Selected VMs stay intact** - Never overwritten by destination updates  
✅ **Destination is platform-aware** - Only relevant fields are populated
✅ **Clear function names** - Each function name describes what it updates
✅ **Isolated updates** - Each function loads, updates, saves independently
✅ **Backward compatible** - Functions also update in-memory variables

---

## Testing the Flow

### To verify the flow works correctly:

1. **STEP 2:** Enter ESXi details → Check `config['source']` is populated
2. **STEP 3:** Select VMs → Check `config['selected_vms']` is updated, source unchanged
3. **STEP 4:** Enter Proxmox details → Check `config['destination'].proxmox_*` is updated
4. **VERIFY:** All three sections should have their respective data intact

### Command to check config.json:
```bash
cat app/config.json | python -m json.tool
```

---

## Migration Script Access

The migration scripts can access configuration easily:

```python
from app.esxi_to_proxmox_migration import (
    ESXI_HOST, ESXI_USER, ESXI_PASS,      # Source
    PROXMOX_HOST, PROXMOX_USER, PROXMOX_PASS,  # Destination
    sel  # Selected VMs
)

# Or reload fresh config anytime:
from app.esxi_to_proxmox_migration import load_config
load_config()  # Reloads all variables from disk
```

---

## Troubleshooting

**Issue:** Destination details overwrite source details
**Fix:** Use `update_destination_proxmox_details()` or `update_destination_kvm_details()` (NOT old function names)

**Issue:** Selected VMs get cleared
**Fix:** Use `update_selected_vm_list()` (NOT `update_selected_vms()` alone)

**Issue:** Old values remain in config
**Fix:** Call `load_config()` in migration module to refresh variables from disk

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-19  
**Status:** ✅ Complete and Tested
