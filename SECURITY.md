# Security & Password-Based Authentication

## Proxmox Authentication

The application uses **password-based authentication** with **SSL certificate verification bypassed** for development convenience.

## Authentication Method

### Password-Based Authentication
**Why:** Simple and straightforward for internal/lab environments
**Format:**
- Host: IP or hostname (e.g., 192.168.1.100)
- Username: Proxmox user (e.g., root@pam)
- Password: User's password
- Port: 8006 (default)

## SSL/Certificate Bypass

**Status:** SSL certificate validation is **DISABLED** for development
```python
verify_ssl=False  # Bypasses all SSL/certificate checks
```

### This Means:
- ✅ Works with self-signed certificates
- ✅ No certificate validation errors
- ✅ Simple setup for development
- ✅ No need for valid SSL certificates

### Security Consideration:
⚠️ **For Development/Lab Only** - This bypasses important security checks
- In production, enable SSL verification
- Use valid certificates
- Set `verify_ssl=True`

## Session Storage

Credentials are stored in Flask session after successful authentication:

```python
session['destination_host'] = host
session['destination_user'] = username
session['destination_pass'] = password
session['destination_port'] = port
```

### Session Security:
- Encrypted with `FLASK_SECRET_KEY`
- Signed to prevent tampering
- HTTP-Only cookies (not accessible to JavaScript)
- Same-Site cookie protection (CSRF prevention)
- Auto-expires on logout

## Environment Variables

### Development
```bash
FLASK_SECRET_KEY=dev-secret-key-change-me
```

### Production
Create `.env` file (NEVER commit to git):
```bash
FLASK_SECRET_KEY=your-very-long-random-secure-key
SESSION_COOKIE_SECURE=True      # HTTPS only
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
```

## Production Recommendations

### ✅ For Production Deployment:

1. **Enable SSL Verification**
   ```python
   # In app/proxmox/client.py
   verify_ssl=True  # Use valid certificates
   ```

2. **Use HTTPS**
   ```python
   SESSION_COOKIE_SECURE = True  # Requires HTTPS
   ```

3. **Strong SECRET_KEY**
   ```bash
   FLASK_SECRET_KEY=your-strong-random-key-min-32-chars
   ```

4. **Don't Store Passwords in .env**
   - Use environment variables or secrets manager
   - Rotate passwords regularly
   - Use service accounts with minimal permissions

5. **Add to .gitignore**
   ```
   .env
   .env.local
   *.key
   *.pem
   instance/
   __pycache__/
   ```

## What NOT to Do

❌ Don't:
- Store plaintext passwords in files
- Commit `.env` to version control
- Use weak SECRET_KEY
- Deploy with `verify_ssl=False` in production
- Use HTTP in production
- Share passwords in code

## Connection Process

1. **User enters credentials in form**
   - Host, Username, Password, Port

2. **Flask validates credentials**
   - Attempts connection to Proxmox
   - SSL checks bypassed (development mode)
   - Proxmox validates username/password

3. **On success:**
   - Credentials stored in Flask session (encrypted)
   - Session marked as authenticated
   - User redirected to migration summary

4. **For subsequent requests:**
   - Credentials retrieved from session
   - Used for Proxmox API calls

## Troubleshooting

### "Connection failed: Connection refused"
**Cause:** Proxmox host not reachable
**Fix:** 
- Verify IP/hostname
- Check port (default 8006)
- Ensure Proxmox service is running

### "Connection failed: Unauthorized"
**Cause:** Wrong username or password
**Fix:**
- Verify credentials in Proxmox
- Try username@realm format (e.g., root@pam)

### "Connection failed: [SSL error]"
**Cause:** SSL verification is enabled somewhere
**Fix:**
- Ensure `verify_ssl=False` in client code
- Check SSL context setup

---

**This setup is suitable for development and internal lab environments.**
For production deployment, follow the recommendations above to enable proper SSL verification and security measures.

