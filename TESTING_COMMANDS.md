# Testing Commands for Proxmox Connection Issues

Run these commands on your **server machine** where you have the application and Proxmox server access.

## Prerequisites

Make sure you are in the project directory:
```powershell
cd "C:\Users\Akshay\OneDrive\Desktop\Python_VS\My_project"
```

Or for Linux/Mac:
```bash
cd /path/to/My_project
```

---

## Step 1: Verify Python Environment and Dependencies

### Check Python Version
```powershell
.\.venv\Scripts\python.exe --version
```

Or on Linux/Mac:
```bash
source .venv/bin/activate
python --version
```

### List All Installed Packages
```powershell
.\.venv\Scripts\python.exe -m pip list
```

Or on Linux/Mac:
```bash
pip list
```

**Expected Output:** Should show `proxmoxer` and `pyvmomi` installed

---

## Step 2: Test Direct Proxmox Connection

### Run the Direct Connection Test Script

First, **UPDATE the credentials** in the test file:

```powershell
.\.venv\Scripts\python.exe -c "
import sys
import ssl
import warnings

warnings.filterwarnings('ignore')
ssl._create_default_https_context = ssl._create_unverified_context

from proxmoxer import ProxmoxAPI

HOST = '192.68.203.32'
USER = 'root@pam'
PASSWORD = 'YOUR_PASSWORD_HERE'
PORT = 8006

print('[TEST] Attempting connection to Proxmox...')
print(f'[TEST] Host: {HOST}:{PORT}')
print(f'[TEST] User: {USER}')

try:
    proxmox = ProxmoxAPI(HOST, user=USER, password=PASSWORD, port=PORT, verify_ssl=False, timeout=10)
    print('[TEST] ✓ Connection successful!')
    
    version = proxmox.version.get()
    print(f'[TEST] ✓ Proxmox Version: {version.get(\"version\", \"unknown\")}')
    
except Exception as e:
    print(f'[TEST] ✗ Connection FAILED: {e}')
    import traceback
    traceback.print_exc()
"
```

Or on Linux/Mac:
```bash
source .venv/bin/activate
python -c "
import sys
import ssl
import warnings

warnings.filterwarnings('ignore')
ssl._create_default_https_context = ssl._create_unverified_context

from proxmoxer import ProxmoxAPI

HOST = '192.68.203.32'
USER = 'root@pam'
PASSWORD = 'YOUR_PASSWORD_HERE'
PORT = 8006

print('[TEST] Attempting connection to Proxmox...')
print(f'[TEST] Host: {HOST}:{PORT}')
print(f'[TEST] User: {USER}')

try:
    proxmox = ProxmoxAPI(HOST, user=USER, password=PASSWORD, port=PORT, verify_ssl=False, timeout=10)
    print('[TEST] ✓ Connection successful!')
    
    version = proxmox.version.get()
    print(f'[TEST] ✓ Proxmox Version: {version.get(\"version\", \"unknown\")}')
    
except Exception as e:
    print(f'[TEST] ✗ Connection FAILED: {e}')
    import traceback
    traceback.print_exc()
"
```

**What to look for:**
- ✓ If you see "Connection successful!" - The credentials and network are working
- ✗ If you see an error - Note the exact error message and provide it

---

## Step 3: Test Network Connectivity to Proxmox Host

### Test if Proxmox Host is Reachable

**On Windows:**
```powershell
ping 192.68.203.32
```

**On Linux/Mac:**
```bash
ping -c 4 192.68.203.32
```

**On Windows (Advanced - Test Specific Port):**
```powershell
Test-NetConnection -ComputerName 192.68.203.32 -Port 8006
```

**Expected Output:** Should show "Connected = True" and receive ping responses

---

## Step 4: Check Flask Server Logs

### Start Flask Server with Debug Output

```powershell
.\.venv\Scripts\python.exe run.py
```

Or on Linux/Mac:
```bash
source .venv/bin/activate
python run.py
```

**You should see:**
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

---

## Step 5: Test the Web Application (While Flask is Running)

Open another terminal/PowerShell window **while Flask is running**:

### Test the /connect-destination endpoint directly

**On Windows:**
```powershell
$headers = @{"X-Requested-With" = "XMLHttpRequest"}
$body = @{
    host = "192.68.203.32"
    username = "root@pam"
    password = "YOUR_PASSWORD_HERE"
    port = "8006"
}

$response = Invoke-WebRequest -Uri "http://127.0.0.1:5000/connect-destination" `
    -Method POST `
    -Headers $headers `
    -Body $body

$response.Content | ConvertFrom-Json | Format-List
```

**On Linux/Mac (using curl):**
```bash
curl -X POST http://127.0.0.1:5000/connect-destination \
  -H "X-Requested-With: XMLHttpRequest" \
  -d "host=192.68.203.32" \
  -d "username=root@pam" \
  -d "password=YOUR_PASSWORD_HERE" \
  -d "port=8006"
```

**Expected Output:**
```json
{
  "success": true,
  "message": "Successfully connected to Proxmox!"
}
```

**If failed, watch the Flask console** for `[ROUTE]` and `[PROXMOX]` debug messages

---

## Step 6: Collect Debug Information

### Check Flask Server Console Output

When you run Step 5's endpoint test, **look at the Flask server console** for lines starting with:
- `[ROUTE]` - Route handler debug messages
- `[PROXMOX]` - Proxmox connection debug messages

Copy the **entire output** and provide it.

### Example of what you should see:
```
[ROUTE] Received POST request to /connect-destination
[ROUTE] Platform: linux/Darwin/Windows
[ROUTE] Validating form inputs...
[ROUTE] host=192.68.203.32, username=root@pam, port=8006
[PROXMOX] Attempting Proxmox connection...
[PROXMOX] Creating ProxmoxAPI instance...
[PROXMOX] Connection successful!
[PROXMOX] Version check successful!
[ROUTE] Storing credentials in session...
[ROUTE] Returning success response
```

---

## Step 7: Troubleshooting Based on Results

### Scenario A: Direct Python Test FAILS (Step 2)
**Problem:** Cannot connect to Proxmox directly from Python
- ✗ Error: `Connection refused`
  - **Check:** Is Proxmox running? Is port 8006 open?
  - **Fix:** Restart Proxmox, check firewall rules
  
- ✗ Error: `Name or service not known` / `getaddrinfo failed`
  - **Check:** Can you ping the host? (Step 3)
  - **Fix:** Verify IP address is correct, check DNS

- ✗ Error: `Authentication failed`
  - **Check:** Are credentials correct? Is user enabled?
  - **Fix:** Verify username and password on Proxmox directly

### Scenario B: Network Test FAILS (Step 3)
**Problem:** Cannot reach Proxmox host at all
- **Fix:** Check firewall, network routing, IP address
- **Command to run:** `tracert 192.68.203.32` (Windows) or `traceroute 192.68.203.32` (Linux/Mac)

### Scenario C: Flask Server Test FAILS (Step 5)
**Problem:** Web endpoint returns error, but direct Python works
- **Check:** Flask console for `[ROUTE]` and `[PROXMOX]` messages
- **Possible issues:** Session storage, environment variables, path issues

### Scenario D: Everything Works but Browser Still Fails
**Problem:** Direct tests pass, but AJAX in browser fails
- **Check:** Browser Developer Tools → Network tab
- **Fix:** May be CORS or browser-specific issue
- **Workaround:** Check if page loads if you refresh or hard refresh (Ctrl+Shift+R)

---

## Step 8: If All Tests Pass

Once all tests pass successfully:

1. **Open the web application:** http://127.0.0.1:5000
2. **Navigate to:** Destination Details form
3. **Enter credentials:**
   - Host: `192.68.203.32`
   - Username: `root@pam`
   - Password: `YOUR_PASSWORD`
   - Port: `8006`
4. **Click:** "Connect to Proxmox"
5. **Expected:** Green success button and redirect

---

## Summary of Commands to Run in Order

### Quick Test Sequence (All on Same Machine)

```powershell
# 1. Navigate to project
cd "C:\Users\Akshay\OneDrive\Desktop\Python_VS\My_project"

# 2. Test network
Test-NetConnection -ComputerName 192.68.203.32 -Port 8006

# 3. Test Python direct connection (UPDATE PASSWORD)
.\.venv\Scripts\python.exe -c "import ssl, warnings; warnings.filterwarnings('ignore'); ssl._create_default_https_context = ssl._create_unverified_context; from proxmoxer import ProxmoxAPI; p = ProxmoxAPI('192.68.203.32', user='root@pam', password='YOUR_PASSWORD', port=8006, verify_ssl=False, timeout=10); print('✓ Success!'); print(p.version.get())"

# 4. Start Flask (keep running)
.\.venv\Scripts\python.exe run.py

# 5. In another terminal, test endpoint (UPDATE PASSWORD)
$body = @{host="192.68.203.32"; username="root@pam"; password="YOUR_PASSWORD"; port="8006"}
Invoke-WebRequest http://127.0.0.1:5000/connect-destination -Method POST -Headers @{"X-Requested-With"="XMLHttpRequest"} -Body $body | % Content | ConvertFrom-Json

# 6. Check Flask console for [ROUTE] and [PROXMOX] messages
```

---

## Report Template

When you run these tests, please provide output in this format:

```
=== TEST RESULTS ===

Step 2 (Direct Python Connection):
[Paste output here]

Step 3 (Network Connectivity):
[Paste output here]

Step 5 (Flask Endpoint Test):
[Paste output here]

Flask Console Messages:
[Paste [ROUTE] and [PROXMOX] messages here]

Any errors:
[Paste error messages here]
```

---

**Need Help?** Make sure to:
- Replace `YOUR_PASSWORD_HERE` with actual Proxmox password
- Check IP address `192.68.203.32` is correct
- Verify port `8006` is correct for your Proxmox installation
- Run commands from the project directory
