# WiFi Tracker - Security & Deployment Guide

## Security Implementation Status

### ✅ OWASP Top 10 Protection

| Vulnerability | Protection | Status |
|---|---|---|
| **Broken Authentication** | Rate limiting (5 attempts/15min), strong password requirements, login attempt logging | ✅ |
| **Broken Access Control** | Simple admin check (can extend to JWT tokens if needed) | ✅ |
| **Injection** | SQLAlchemy ORM prevents SQL injection, input validation for all fields | ✅ |
| **Insecure Deserialization** | Pydantic validation on all inputs | ✅ |
| **Broken Validation** | Client & server-side validation: MAC format, room/area alphanumeric, SSID length | ✅ |
| **Sensitive Data Exposure** | Environment variables for credentials, HSTS headers, CSP headers | ✅ |
| **Authentication Bypass** | Timing-attack resistant comparison, rate limiting | ✅ |
| **XXE/File Upload** | No file upload functionality | ✅ |
| **Weak/Broken Crypto** | Use HTTPS only (production), secure headers | ✅ |
| **Insufficient Logging** | Request logging on all endpoints | ✅ |

---

## Pre-Deployment Setup (Windows Local)

### 1. Environment Variables
Create `.env` file in project root:

```bash
# Copy .env.example to .env
copy .env.example .env
```

**Edit .env with secure values:**
```env
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=GenerateSecurePassword_Min12Chars
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
ENVIRONMENT=development
SECRET_KEY=your_secret_key_here
ALLOWED_HOSTS=localhost,127.0.0.1
```

**Generate strong password:**
```powershell
# PowerShell
[System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((1..32 | ForEach-Object {[char][Random]::new().Next(33,127)}))) -split '' | Where-Object {$_} | Select-Object -First 16 | Join-String
```

### 2. Install python-dotenv
```powershell
pip install python-dotenv
```

### 3. Load environment variables in run.py
Add to the top of `run.py`:
```python
from dotenv import load_dotenv
import os
load_dotenv()
```

### 4. Update routes.py imports
Already done ✅

---

## Production Deployment on DigitalOcean Droplet

### Prerequisites
- GitHub Student Pack account with DigitalOcean credits
- SSH key pair (already have one if using GitHub)
- DigitalOcean account setup

### Step 1: Create Droplet
```bash
# On DigitalOcean Dashboard:
# - Choose: Ubuntu 22.04 LTS
# - Size: Basic $5/month (or $12 for more reliability)
# - Region: Choose closest to your users
# - Add SSH key (use GitHub SSH key)
# - Hostname: wifi-tracker
```

### Step 2: SSH into Droplet
```bash
ssh root@your_droplet_ip
```

### Step 3: Initial Server Setup
```bash
# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3.11 python3-pip python3-venv git curl

# Create app directory
mkdir -p /opt/wifi-tracker
cd /opt/wifi-tracker

# Clone your repository
git clone https://github.com/yourusername/wifi-tracker.git .
```

### Step 4: Setup Python Environment
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Configure Environment Variables
```bash
# Create .env file
nano .env
```

**Paste the following (update with your values):**
```env
ADMIN_USERNAME=secureadminname
ADMIN_PASSWORD=YourVerySecurePassword_Min16Chars
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
ENVIRONMENT=production
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your_droplet_ip
```

**Save: CTRL+X → Y → Enter**

### Step 6: Setup Systemd Service
Create systemd service file:
```bash
sudo nano /etc/systemd/system/wifi-tracker.service
```

**Paste:**
```ini
[Unit]
Description=WiFi Tracker Application
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/wifi-tracker
Environment="PATH=/opt/wifi-tracker/venv/bin"
ExecStart=/opt/wifi-tracker/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Save: CTRL+X → Y → Enter**

### Step 7: Enable and Start Service
```bash
sudo chown -R www-data:www-data /opt/wifi-tracker
sudo systemctl daemon-reload
sudo systemctl enable wifi-tracker
sudo systemctl start wifi-tracker
sudo systemctl status wifi-tracker
```

### Step 8: Setup Nginx Reverse Proxy
```bash
# Install Nginx
apt install -y nginx

# Create Nginx config
sudo nano /etc/nginx/sites-available/wifi-tracker
```

**Paste:**
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # SSL certificates (generate with Certbot below)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Save: CTRL+X → Y → Enter**

### Step 9: Setup Free SSL Certbot
```bash
# Install Certbot
apt install -y certbot python3-certbot-nginx

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com

# Enable Nginx site
sudo ln -s /etc/nginx/sites-available/wifi-tracker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 10: Setup Firewall
```bash
# Enable UFW
ufw enable

# Allow SSH, HTTP, HTTPS
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw status
```

### Step 11: Setup Automatic Backups
```bash
# Create backup script
sudo nano /opt/wifi-tracker/backup.sh
```

**Paste:**
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/wifi-tracker/backups"
mkdir -p $BACKUP_DIR
cp /opt/wifi-tracker/wifi_tracker.db $BACKUP_DIR/wifi_tracker_$DATE.db
# Keep only last 30 days of backups
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
```

**Make executable and add to crontab:**
```bash
chmod +x /opt/wifi-tracker/backup.sh
sudo crontab -e
# Add line: 0 2 * * * /opt/wifi-tracker/backup.sh
```

---

## Security Checklist Before Going Live

- [ ] Changed ADMIN_USERNAME and ADMIN_PASSWORD in `.env`
- [ ] Generated strong SECRET_KEY
- [ ] Set ENVIRONMENT=production in `.env`
- [ ] Updated ALLOWED_HOSTS with your domain
- [ ] Configured Telegram bot token (if using alerts)
- [ ] Setup SSL certificate with Certbot
- [ ] Firewall is configured (UFW enabled)
- [ ] Backup script running daily
- [ ] Tested login with rate limiting (test with wrong password 5x)
- [ ] Verified HTTPS redirect working
- [ ] Tested all CRUD operations
- [ ] Verified security headers in browser DevTools

---

## Security Headers Verification

Test your headers at: https://securityheaders.com/

**Expected headers:**
- ✅ Content-Security-Policy
- ✅ X-Content-Type-Options: nosniff
- ✅ X-Frame-Options: DENY
- ✅ Strict-Transport-Security
- ✅ Referrer-Policy

---

## Monitoring & Logging

### Check Application Logs
```bash
sudo journalctl -u wifi-tracker -f
```

### Check Nginx Logs
```bash
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Monitor CPU/Memory
```bash
top
# or
htop
```

---

## Future Security Enhancements

1. **JWT Authentication** - Replace simple login with JWT tokens
2. **Database Encryption** - Encrypt sensitive fields in SQLite
3. **Audit Logging** - Log all client modifications with timestamps
4. **2FA** - Add TOTP/SMS 2FA for admin login
5. **Secrets Management** - Use Hashicorp Vault or DigitalOcean Secrets
6. **Rate Limiting** - Per-IP rate limiting using Redis
7. **WAF** - CloudFlare or ModSecurity for advanced filtering

---

## Troubleshooting

**Port already in use:**
```bash
lsof -i :8000
kill -9 <PID>
```

**SSL certificate issues:**
```bash
sudo certbot renew --dry-run
```

**Check service status:**
```bash
sudo systemctl status wifi-tracker
```

**View recent logs:**
```bash
sudo journalctl -u wifi-tracker -n 50
```

---

## Questions?
For security issues or questions, please create an issue on GitHub.
