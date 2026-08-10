# VPS Deployment Guide

This guide explains how to deploy the WiFi Payment Tracker on a Linux VPS using a virtual environment and systemd.

## 1. Prerequisites

- A Linux VPS (Ubuntu/Debian recommended)
- Python 3.12+ installed
- `git` installed
- `pip` and `venv`
- Optional: `nginx` for reverse proxy

## 2. Clone the repository

```bash
cd /opt
sudo git clone https://your-repo-url.git wifi-tracker
cd wifi-tracker
```

## 3. Create and activate the virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Configure environment variables

Create a `.env` file in the project root. Example values:

```ini
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secret_password
SECRET_KEY=supersecretkey
ENVIRONMENT=production
DATABASE_URL=sqlite:///./wifi_tracker.db
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
ALLOWED_HOSTS=localhost,127.0.0.1,your-vps-domain
SCHEDULER_TIMEZONE=Asia/Phnom_Penh
HOST=0.0.0.0
PORT=8000
```

> If you use SQLite, the database file will be created in the project root as `wifi_tracker.db`.

## 5. Test locally

With the virtual environment activated:

```bash
python run.py
```

Open `http://localhost:8000` to verify the app starts.

## 6. Create a systemd service

Create `/etc/systemd/system/wifi-tracker.service` with the following contents:

```ini
[Unit]
Description=WiFi Payment Tracker
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/wifi-tracker
EnvironmentFile=/opt/wifi-tracker/.env
ExecStart=/opt/wifi-tracker/.venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Adjust `User` and `Group` as needed for your VPS.

## 7. Enable and start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable wifi-tracker.service
sudo systemctl start wifi-tracker.service
sudo systemctl status wifi-tracker.service
```

## 8. Optional: Configure nginx reverse proxy

Install nginx:

```bash
sudo apt update
sudo apt install nginx
```

Create `/etc/nginx/sites-available/wifi-tracker`:

```nginx
server {
    listen 80;
    server_name your-vps-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/wifi-tracker/frontend/static/;
    }
}
```

Enable the site and reload nginx:

```bash
sudo ln -s /etc/nginx/sites-available/wifi-tracker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 9. Manage the service

```bash
sudo systemctl restart wifi-tracker.service
sudo systemctl stop wifi-tracker.service
sudo journalctl -u wifi-tracker.service -f
```

## 10. Notes

- Use `ENVIRONMENT=production` in your `.env` file.
- If using a database other than SQLite, update `DATABASE_URL` accordingly.
- The scheduler is built into the app, so starting the service is enough to enable daily alerts.
- If you change code, restart the service instead of running with `reload=True` in production.

## 11. Troubleshooting

- If the app fails to start, check logs:
  ```bash
  sudo journalctl -u wifi-tracker.service -e
  ```
- If nginx proxy issues occur, test with:
  ```bash
  curl -I http://127.0.0.1:8000
  ```

## 12. Security

- Keep `.env` private and outside version control.
- Use strong values for `ADMIN_PASSWORD` and `SECRET_KEY`.
- Limit access to the VPS and firewall ports to only what you need.
