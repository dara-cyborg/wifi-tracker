from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import os
from backend.db.session import SessionLocal
from backend.business.client_service import get_overdue_clients, get_active_clients, get_not_set_clients
from backend.infrastructure.notify import send_telegram_message

scheduler = BackgroundScheduler()
SCHEDULER_TIMEZONE = os.getenv("SCHEDULER_TIMEZONE", "Asia/Phnom_Penh")


def daily_payment_alert():
    db = SessionLocal()
    try:
        overdue = get_overdue_clients(db)
        active = get_active_clients(db)
        not_set = get_not_set_clients(db)

        message = ""
        for client, status in overdue:
            message += f"• {client.room_number} - {client.area} ({status})\n"

        send_telegram_message(message)
    except Exception:
        pass
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(
        daily_payment_alert,
        CronTrigger(hour=6, minute=0, timezone=SCHEDULER_TIMEZONE),
        id="daily_payment_alert",
        name="Daily Payment Alert at 6 AM"
    )
    scheduler.start()


def stop_scheduler():
    scheduler.shutdown()
