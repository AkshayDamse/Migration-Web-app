# VM Migration Web App (Flask)

This project is a starting scaffold for a full-stack web application to migrate VMs between virtualization platforms (example: ESXi -> Proxmox/KVM). It includes a Flask backend, templates, a pyvmomi-based ESXi client and clear comments to help you extend it.

What's included
- Flask app factory and blueprint (`app/`)
- A small VMware client using `pyvmomi` (`app/vmware/client.py`) to connect to ESXi and list VMs
- Multi-step UI: select platforms -> enter source credentials -> list and select VMs -> migration stub
- `requirements.txt` with minimal dependencies

Quick start (Windows PowerShell)

1. Create a virtualenv and activate it

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2. Install requirements

```powershell
pip install -r requirements.txt
```

3. Run the app

```powershell
python run.py
```

4. Open http://127.0.0.1:5000

Notes and next steps
- This scaffold only implements the connect & list flow for ESXi using `pyvmomi` and stubs migration.
- For production: add validation, secrets management, background workers for long-running migrations, RBAC, persistent storage, logging, and tests.
- See file comments for guidance on where to extend functionality.

Security note
- DO NOT commit real credentials. Use environment variables or a secrets manager for production usage.
