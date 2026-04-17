from datetime import date
from sqlalchemy.orm import Session
from backend.models import Client
import calendar


def get_current_month_due_date(due_day: int) -> date:
    """Get the due date for the current month based on due_day"""
    today = date.today()
    max_day = calendar.monthrange(today.year, today.month)[1]
    clamped_day = min(due_day, max_day)
    return today.replace(day=clamped_day)


def get_client_status(client: Client) -> str:
    """
    Determine client payment status:
    - "Not set" - no payment recorded
    - "Active" - paid for current period
    - "N days overdue" - past due day without payment
    """
    if not client.last_payment:
        return "Not set"
    
    today = date.today()
    current_due_date = get_current_month_due_date(client.due_day)
    
    # If today is before or on the due date
    if today <= current_due_date:
        # Check if payment is from current period (on or after start of month)
        month_start = today.replace(day=1)
        if client.last_payment >= month_start:
            return "Active"
    else:
        # Today is after the due date
        # Check if payment was made before due date
        if client.last_payment >= current_due_date:
            return "Active"
    
    # Past due without payment
    days_overdue = (today - current_due_date).days
    return f"{days_overdue} days overdue"


def get_overdue_clients(db: Session):
    """Get all clients overdue (not 'Active' and not 'Not set')"""
    all_clients = db.query(Client).all()
    overdue = []
    for client in all_clients:
        status = get_client_status(client)
        if status != "Not set" and status != "Active":
            overdue.append((client, status))
    return overdue


def get_active_clients(db: Session):
    """Get all clients with 'Active' status"""
    all_clients = db.query(Client).all()
    active = []
    for client in all_clients:
        if get_client_status(client) == "Active":
            active.append(client)
    return active


def get_not_set_clients(db: Session):
    """Get all clients with 'Not set' status"""
    all_clients = db.query(Client).all()
    not_set = []
    for client in all_clients:
        if get_client_status(client) == "Not set":
            not_set.append(client)
    return not_set


def format_alert_message(overdue, active, not_set):
    message = "🔔 PAYMENT ALERT - 6 AM Check\n\n"
    
    if overdue:
        message += f"⚠️ មិនទាន់បង់មាន ({len(overdue)} នាក់):\n"
        for client, status in overdue:
            message += f"• បន្ទប់លេខ {client.room_number} - {client.area} ({status})\n"
        message += "\n"
    
    if active:
        message += f"✅ បង់ហើយមាន ({len(active)} នាក់):\n"
        for client in active:
            message += f"• បន្ទប់លេខ {client.room_number} - {client.area}\n"
        message += "\n"
    
    if not_set:
        message += f"⏳ មិនទាន់បង់មាន ({len(not_set)} នាក់):\n"
        for client in not_set:
            message += f"• បន្ទប់លេខ {client.room_number} - {client.area}\n"
    
    return message
