"""
SSH runner to execute migration script on remote KVM host.

Features:
- Uses Paramiko to SSH to the destination KVM host
- Uploads `kvm_migration.py` via SFTP
- Executes the script in a remote shell and streams stdout/stderr
- Stores logs in memory (simple) and exposes job IDs and status

Notes:
- This is a simple implementation for development. For production, use a job queue
  (Celery/RQ) and persistent storage for logs.
- Similar to ssh_runner.py but specifically for KVM platform
"""
import threading
import uuid
import time
import os
import io
import posixpath
from typing import Dict, Any

try:
    import paramiko
except ImportError:  # pragma: no cover
    paramiko = None

JOBS: Dict[str, Dict[str, Any]] = {}


class SSHRunnerError(Exception):
    pass


def start_kvm_migration(host: str, username: str, password: str, port: int = 22, remote_path: str = '/home/kvmuser', 
                        local_script: str = 'app/kvm_migration.py', config_path: str = 'app/config.json') -> str:
    """Start a background job that uploads and runs the KVM migration script on remote host.
    
    Returns a job id that can be polled using `get_job_status(job_id)`.
    """
    if paramiko is None:
        raise SSHRunnerError("paramiko is not installed. Install with: pip install paramiko")

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        'status': 'queued',
        'logs': [],
        'started_at': time.time(),
        'finished_at': None,
        'exit_code': None,
    }

    def _run():
        JOBS[job_id]['status'] = 'running'
        logs = JOBS[job_id]['logs']
        client = None
        try:
            logs.append(f"Connecting to {host}:{port} as {username}...")
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=host, port=port, username=username, password=password, timeout=15)
            logs.append("SSH connection established.")

            sftp = client.open_sftp()
           
            # Upload migration script         
            local_script_path = os.path.join(os.getcwd(), local_script)
            if not os.path.exists(local_script_path):
                # Fallback: try the bundled migration script inside app/
                fallback = os.path.join(os.getcwd(), 'app', 'kvm_migration.py')
                if os.path.exists(fallback):
                    logs.append(f"Local script not found at {local_script_path}, falling back to {fallback}")
                    local_script_path = fallback
                else:
                    raise SSHRunnerError(f"Local KVM migration script not found: {local_script_path}")
            remote_script = posixpath.join(remote_path, os.path.basename(local_script))
            logs.append(f"Uploading {local_script_path} to {remote_script}...")
            sftp.put(local_script_path, remote_script)
            sftp.chmod(remote_script, 0o755)

            # Upload config.json
            config_local_path = os.path.join(os.getcwd(), config_path)
            if os.path.exists(config_local_path):
                remote_config = posixpath.join(remote_path, 'config.json')
                logs.append(f"Uploading {config_local_path} to {remote_config}...")
                sftp.put(config_local_path, remote_config)
                logs.append("Config upload complete")
            else:
                logs.append(f"Warning: Config.json not found at {config_local_path}, skipping upload.")

            sftp.close()
            logs.append("Upload complete.")

            # Execute the script as root using sudo with -S flag to read password from stdin
            cmd = f'sudo -S python3 -u {remote_script}'
            logs.append(f"Executing as root: {cmd}")
            stdin, stdout, stderr = client.exec_command(cmd)
            
            # Send password for sudo via stdin
            stdin.write(password + '\n')
            stdin.flush()

            # Stream output
            for line in iter(lambda: stdout.readline(2048), ""):
                if not line:
                    break
                logs.append(line.rstrip())

            # Stream stderr
            for line in iter(lambda: stderr.readline(2048), ""):
                if not line:
                    break
                logs.append(f"[STDERR] {line.rstrip()}")

            exit_code = stdout.channel.recv_exit_status()
            JOBS[job_id]['exit_code'] = exit_code
            
            if exit_code == 0:
                logs.append(f"[SUCCESS] KVM migration script exited with code {exit_code}")
                JOBS[job_id]['status'] = 'finished'
            else:
                logs.append(f"[ERROR] KVM migration script exited with code {exit_code}")
                JOBS[job_id]['status'] = 'failed'
            
            JOBS[job_id]['finished_at'] = time.time()

        except SSHRunnerError as e:
            logs.append(f"[ERROR] {str(e)}")
            JOBS[job_id]['status'] = 'failed'
            JOBS[job_id]['finished_at'] = time.time()
        except paramiko.AuthenticationException as e:
            logs.append(f"[ERROR] SSH authentication failed: {str(e)}")
            JOBS[job_id]['status'] = 'failed'
            JOBS[job_id]['finished_at'] = time.time()
        except Exception as e:
            logs.append(f"[ERROR] {str(e)}")
            JOBS[job_id]['status'] = 'failed'
            JOBS[job_id]['finished_at'] = time.time()
        finally:
            if client:
                client.close()

    # Run in background thread
    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return job_id


def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get current status and logs for a job."""
    if job_id not in JOBS:
        raise SSHRunnerError(f"Job not found: {job_id}")
    return JOBS[job_id].copy()


def clear_job(job_id: str) -> None:
    """Clear a completed job from memory."""
    if job_id in JOBS:
        del JOBS[job_id]
