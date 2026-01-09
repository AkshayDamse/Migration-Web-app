"""
SSH runner to execute migration script on remote Proxmox host.

Features:
- Uses Paramiko to SSH to the destination host
- Uploads `esxi_to_proxmox_migration.py` via SFTP
- Executes the script in a remote shell and streams stdout/stderr
- Stores logs in memory (simple) and exposes job IDs and status

Notes:
- This is a simple implementation for development. For production, use a job queue
  (Celery/RQ) and persistent storage for logs.
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


def start_remote_migration(host: str, username: str, password: str, port: int = 22, remote_path: str = '/root', 
                           local_script: str =r'\Users\oranlab\Desktop\Development\Migration-Web-app-main\Migration-Web-app-main\app\mscript.py', config_path: str = r'\Users\oranlab\Desktop\Development\Migration-Web-app-main\Migration-Web-app-main\app\config.json') -> str:
    """Start a background job that uploads and runs the migration script on remote host.
    
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
                fallback = os.path.join(os.getcwd(), 'app', 'mscript.py')
                if os.path.exists(fallback):
                    logs.append(f"Local script not found at {local_script_path}, falling back to {fallback}")
                    local_script_path = fallback
                else:
                    raise SSHRunnerError(f"Local script not found: {local_script_path}")
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

            # Execute the script; ensure python3 is used
            cmd = f'python3 -u {remote_script}'
            logs.append(f"Executing: {cmd}")
            stdin, stdout, stderr = client.exec_command(cmd)

            # Stream output
            for line in iter(lambda: stdout.readline(2048), ""):
                if not line:
                    break
                logs.append(line.rstrip())

            err = stderr.read().decode(errors='replace')
            if err:
                logs.append("--- STDERR ---")
                logs.extend(err.splitlines())

            exit_status = stdout.channel.recv_exit_status()
            JOBS[job_id]['exit_code'] = exit_status
            JOBS[job_id]['status'] = 'finished' if exit_status == 0 else 'failed'
            JOBS[job_id]['finished_at'] = time.time()
            logs.append(f"Remote script exited with code {exit_status}")

            # Cleanup: delete uploaded files from remote
            try:
                sftp2 = client.open_sftp()
                remote_script_path = os.path.join(remote_path, os.path.basename(local_script))
                remote_config_path = os.path.join(remote_path, 'config.json')
                
                try:
                    sftp2.remove(remote_script_path)
                    logs.append(f"Deleted remote script: {remote_script_path}")
                except Exception as e:
                    logs.append(f"Warning: could not delete {remote_script_path}: {e}")
                
                try:
                    sftp2.remove(remote_config_path)
                    logs.append(f"Deleted remote config: {remote_config_path}")
                except Exception as e:
                    logs.append(f"Warning: could not delete {remote_config_path}: {e}")
                
                sftp2.close()
            except Exception as e:
                logs.append(f"Warning: cleanup failed: {e}")

            client.close()
        except Exception as e:
            JOBS[job_id]['status'] = 'failed'
            JOBS[job_id]['finished_at'] = time.time()
            logs.append(f"Exception: {e}")
            if client:
                try:
                    # Attempt cleanup even on failure
                    sftp_cleanup = client.open_sftp()
                    remote_script_path = os.path.join(remote_path, os.path.basename(local_script))
                    remote_config_path = os.path.join(remote_path, 'config.json')
                    try:
                        sftp_cleanup.remove(remote_script_path)
                    except Exception:
                        pass
                    try:
                        sftp_cleanup.remove(remote_config_path)
                    except Exception:
                        pass
                    sftp_cleanup.close()
                except Exception:
                    pass
                client.close()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return job_id


def get_job_status(job_id: str) -> Dict[str, Any]:
    job = JOBS.get(job_id)
    if not job:
        raise SSHRunnerError("Job not found")
    return job
