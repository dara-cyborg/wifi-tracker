# WiFi Payment Tracker - MVP

Simple payment tracking system for internet clients with daily Telegram alerts.

## Features

✅ **Client Management** - Add/edit clients with room number, area, SSID, MAC, due date  
✅ **Payment Tracking** - Track last payment date  
✅ **Unique MAC Tracking** - One room can have multiple devices (different MACs)  
✅ **Daily Alerts** - Automatic 6 AM Cambodia time alert via Telegram  
✅ **Alert Categories** - Overdue (past due date), Due Soon (3 days), Active (paid & not overdue)  
✅ **Admin Login** - Simple username/password protection  
✅ **Responsive UI** - Simple HTML forms for CRUD operations  

## Tech Stack

- **Backend**: FastAPI + SQLite + SQLAlchemy
- **Scheduler**: APScheduler (6 AM Cambodia timezone)
- **Notifications**: Telegram Bot API
- **Frontend**: Jinja2 + HTML/CSS/JavaScript
- **Database**: SQLite (lightweight, no setup required)

## Project Structure

```
wifi-tracker/
├── backend/
│   ├── __init__.py
│   ├── main.py           # FastAPI app entry point
│   ├── models.py         # SQLAlchemy Client model
│   ├── database.py       # Database setup
│   ├── routes.py         # API endpoints (CRUD + login)
│   ├── services.py       # Alert logic (overdue, due soon)
│   ├── scheduler.py      # APScheduler at 6 AM
│   └── notify.py         # Telegram bot integration
├── frontend/
│   ├── static/
│   │   └── app.js
│   └── templates/
│       ├── index.html    # Client list
│       ├── add.html      # Add client form
│       └── edit.html     # Edit client form
├── run.py                # Entry point to start server
├── requirements.txt      # Python dependencies
└── .env.example          # Environment variables template
```

## Setup & Installation

### 1. Clone and Install Dependencies

```bash
cd wifi-tracker
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your Telegram credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

**How to get Telegram credentials:**
1. Create a bot via [@BotFather](https://t.me/botfather) on Telegram
2. Get your bot token
3. Send a message to your bot, then check chat ID via: `https://api.telegram.org/bot<TOKEN>/getUpdates`

### 3. Run the Application

```bash
python run.py
```

Server starts at `http://localhost:8000`

## Usage

### Web Interface

- **`http://localhost:8000`** - View all clients
- **`http://localhost:8000/add.html`** - Add new client
- **`http://localhost:8000/edit.html?id=ROOM_NUMBER`** - Edit client

### API Endpoints

**Clients**
- `GET /clients` - List all clients
- `GET /clients/{mac}` - Get single client by MAC address
- `POST /clients` - Create client (MAC is unique identifier)
- `PUT /clients/{mac}` - Update client by MAC address
- `DELETE /clients/{mac}` - Delete client by MAC address

**Authentication**
- `POST /login` - Login (request: `{"username": "admin", "password": "admin123"}`)

### Default Admin Credentials

⚠️ **Change these before deploying!**
- Username: `admin`
- Password: `admin123`

To change, edit `backend/routes.py`:
```python
ADMIN_USERNAME = "your_username"
ADMIN_PASSWORD = "your_password"
```

## How Daily Alerts Work

1. **Scheduler** runs at 6 AM Cambodia time every day
2. **Services** queries database for:
   - **Overdue**: `today > due_date`
   - **Due Soon**: `today ≤ due_date ≤ today + 3 days` (and has paid before)
   - **Active**: `last_payment exists` AND `today ≤ due_date`
3. **Format** alert message with room numbers and areas
4. **Send** grouped summary via Telegram bot

### Alert Message Example

```
🔔 PAYMENT ALERT - 6 AM Check

⚠️ OVERDUE (2 clients):
• Room 101 - Building A
• Room 102 - Building B

⏰ DUE SOON (3 days) (1 client):
• Room 201 - Building A

✅ ACTIVE (5 clients):
• Room 301 - Building C
• Room 302 - Building C
...
```

## Deployment (Free Tier Guide)

### Option 1: Railway (Recommended for MVP)
1. Push to GitHub
2. Connect repo to Railway.app
3. Set environment variables in Railway dashboard
4. Add database service (Railway's PostgreSQL free tier)
5. Deploy

### Option 2: Render
1. Push to GitHub
2. Create new Web Service on Render.com
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add free PostgreSQL database
6. Set environment variables

### Option 3: Replit
1. Fork project to Replit
2. Set environment variables in Secrets
3. Run `python run.py`
4. Use Replit's free domain
5. ⚠️ Note: Replit free tier may suspend scheduler if no requests for 30 min

## Database

Uses SQLite for MVP (included in code). For production free tier:
- **Railway**: Use PostgreSQL free tier
- **Render**: Use PostgreSQL free tier
- **Update**: Change `DATABASE_URL` in `backend/database.py`

## Troubleshooting

### Alerts not sending?
- Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
- Test with manual API call: `POST /login` should work
- Check server logs (run with `--reload` flag)

### Database errors?
- Delete `wifi_tracker.db` to reset
- Restart server

### Timezone issues?
- APScheduler uses `Asia/Phnom_Penh` timezone (Cambodia)
- To change: Edit `backend/scheduler.py` line with `timezone="..."`

## Future Improvements (Post-MVP)

- [ ] Database migration system (Alembic)
- [ ] Payment history/transaction log
- [ ] Multiple admin users
- [ ] Email alerts
- [ ] SMS alerts via twilio
- [ ] Payment reminders (2-day warning)
- [ ] Dashboard with charts
- [ ] Bulk client import (CSV)
- [ ] API documentation (Swagger UI)

## Notes

- **Simple & maintainable** - Everything is flat, no unnecessary abstractions
- **Junior-friendly** - Code is readable and easy to extend
- **Production-ready setup** - Easy to scale to free tier cloud
- **Single responsibility** - Each function does one thing

## License

MIT
