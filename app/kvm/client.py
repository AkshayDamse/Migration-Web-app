"""
KVM client for retrieving VM information via SSH and virsh.
"""

def get_kvm_vms(host: str, username: str, password: str, port: int = 22) -> list:
    """
    Get list of VMs from KVM host using SSH and virsh commands.
    
    Args:
        host: KVM host IP or hostname
        username: SSH username
        password: SSH password
        port: SSH port (default 22)
    
    Returns:
        list: List of VM dictionaries with details
        
    Raises:
        Exception on failures
    """
    import paramiko
    
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=host, port=int(port), username=username, password=password, timeout=15)
    except Exception as e:
        raise Exception(f'Could not SSH to KVM host {host}: {e}')
    
    def run(cmd):
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        return out, err
    
    try:
        # Get list of all VMs
        out, err = run("virsh -c qemu://system list --all --name")
        if err:
            raise Exception(f'virsh list failed: {err}')
        
        vm_names = [name for name in out.split('\n') if name.strip()]
        
        vms = []
        for vm_name in vm_names:
            vm_name = vm_name.strip()
            if not vm_name:
                continue
            
            try:
                # Get VM info
                out, err = run(f"virsh -c qemu://system dominfo {vm_name}")
                if err:
                    print(f"Warning: Could not get info for VM {vm_name}: {err}")
                    continue
                
                vm_info = {}
                for line in out.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        vm_info[key.strip().lower()] = value.strip()
                
                # Get CPU count
                cpu = int(vm_info.get('cpu(s)', 0))
                
                # Get memory (convert to MB)
                max_memory = vm_info.get('max memory', '0 KiB')
                if 'KiB' in max_memory:
                    memory_kb = int(max_memory.replace(' KiB', ''))
                    memory_mb = memory_kb // 1024
                elif 'MiB' in max_memory:
                    memory_mb = int(max_memory.replace(' MiB', ''))
                else:
                    memory_mb = 0
                
                # Get disk info
                out, err = run(f"virsh -c qemu://system domblklist {vm_name}")
                storage_gb = 0.0
                if not err:
                    lines = out.split('\n')
                    for line in lines[2:]:  # Skip header
                        parts = line.split()
                        if len(parts) >= 2:
                            disk_path = parts[1]
                            if disk_path != '-':
                                # Get disk size
                                size_out, size_err = run(f"qemu-img info {disk_path} | grep 'virtual size'")
                                if not size_err and size_out:
                                    # Parse "virtual size: 10G (10737418240 bytes)"
                                    size_str = size_out.split(':')[1].split('(')[0].strip()
                                    if 'G' in size_str:
                                        storage_gb += float(size_str.replace('G', ''))
                                    elif 'M' in size_str:
                                        storage_gb += float(size_str.replace('M', '')) / 1024
                
                # Get network interfaces
                out, err = run(f"virsh -c qemu://system domiflist {vm_name}")
                network = []
                if not err:
                    lines = out.split('\n')
                    for line in lines[2:]:  # Skip header
                        parts = line.split()
                        if len(parts) >= 3:
                            network.append(parts[2])  # Interface name
                
                # SCSI controller - KVM typically uses virtio or IDE
                scsi_controller = 'virtio'  # Default for KVM
                
                vms.append({
                    'name': vm_name,
                    'cpu': cpu,
                    'memory': memory_mb,
                    'total_storage_gb': storage_gb,
                    'network': network,
                    'scsi_controller': scsi_controller
                })
                
            except Exception as e:
                print(f"Warning: Error processing VM {vm_name}: {e}")
                continue
        
        client.close()
        return vms
        
    except Exception as e:
        client.close()
        raise Exception(f'Failed to get KVM VMs: {e}')