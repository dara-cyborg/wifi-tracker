from datetime import datetime, date, timedelta
from sqlalchemy import or_
from sqlalchemy.orm import Session
from backend.models import Client


def get_overdue_clients(db: Session):
    today = date.today()
    return db.query(Client).filter(
        Client.due_date < today,
        or_(
            Client.last_payment.is_(None),
            Client.last_payment < Client.due_date
        )
    ).all()


def get_due_soon_clients(db: Session):
    today = date.today()
    three_days_later = today + timedelta(days=3)
    return db.query(Client).filter(
        Client.due_date >= today,
        Client.due_date <= three_days_later,
        Client.last_payment.isnot(None)
    ).all()


def get_active_clients(db: Session):
    today = date.today()
    return db.query(Client).filter(
        Client.last_payment.isnot(None),
        Client.due_date >= today
    ).all()


def format_alert_message(overdue, due_soon, active):
    message = "🔔 PAYMENT ALERT - 6 AM Check\n\n"
    
    if overdue:
        message += f"⚠️ មិនទាន់បង់មាន ({len(overdue)} នាក់):\n"
        for client in overdue:
            message += f"• បន្ទប់លេខ {client.room_number} - {client.area}\n"
        message += "\n"
    
    if due_soon:
        message += f"⏰ សល់ 3 ថ្ងៃមាន ({len(due_soon)} នាក់):\n"
        for client in due_soon:
            message += f"• បន្ទប់លេខ {client.room_number} - {client.area}\n"
        message += "\n"
    
    if active:
        message += f"✅ បង់ហើយមាន ({len(active)} នាក់):\n"
        for client in active:
            message += f"• បន្ទប់លេខ {client.room_number} - {client.area}\n"
    
    return message
