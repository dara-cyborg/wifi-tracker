from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.database import SessionLocal
from backend.services import get_overdue_clients, get_due_soon_clients, get_active_clients, format_alert_message
from backend.notify import send_telegram_message

scheduler = BackgroundScheduler()


def daily_payment_alert():
    db = SessionLocal()
    try:
        overdue = get_overdue_clients(db)
        due_soon = get_due_soon_clients(db)
        active = get_active_clients(db)
        
        message = format_alert_message(overdue, due_soon, active)
        send_telegram_message(message)
        print("[OK] Daily alert job executed")
    except Exception as e:
        print(f"[ERROR] Alert job failed: {e}")
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(
        daily_payment_alert,
        CronTrigger(hour=6, minute=0, timezone="Asia/Phnom_Penh"),
        id="daily_payment_alert",
        name="Daily Payment Alert at 6 AM Cambodia Time"
    )
    scheduler.start()
    print("[OK] Scheduler started")


def stop_scheduler():
    scheduler.shutdown()
