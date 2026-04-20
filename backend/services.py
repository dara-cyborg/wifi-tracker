from datetime import date
from sqlalchemy.orm import Session
from backend.models import Client
import calendar
import os


def get_current_month_due_date(due_day: int) -> date:
    today = date.today()
    max_day = calendar.monthrange(today.year, today.month)[1]
    clamped_day = min(due_day, max_day)
    return today.replace(day=clamped_day)


def get_client_status(client: Client) -> str:
    if not client.last_payment:
        return "Not set"
    
    today = date.today()
    current_due_date = get_current_month_due_date(client.due_day)
    
    if today <= current_due_date:
        month_start = today.replace(day=1)
        if client.last_payment >= month_start:
            return "Active"
    else:
        if client.last_payment >= current_due_date:
            return "Active"
    
    days_overdue = (today - current_due_date).days
    if days_overdue < 0:
        return "Active"
    return f"{days_overdue} days overdue"


def get_overdue_clients(db: Session):
    all_clients = db.query(Client).all()
    overdue = []
    for client in all_clients:
        status = get_client_status(client)
        if status != "Not set" and status != "Active":
            overdue.append((client, status))
    return overdue


def get_active_clients(db: Session):
    all_clients = db.query(Client).all()
    active = []
    for client in all_clients:
        if get_client_status(client) == "Active":
            active.append(client)
    return active


def get_not_set_clients(db: Session):
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


def count_unique_devices_in_room(room_number: str, db: Session) -> int:
    count = db.query(Client).filter(Client.room_number == room_number).count()
    return count


def calculate_room_price(room_number: str, db: Session, price_per_device: float = None) -> float:
    if price_per_device is None:
        price_per_device = float(os.getenv("PRICE_PER_DEVICE_PER_MONTH", "2.5"))
    
    device_count = count_unique_devices_in_room(room_number, db)
    total_price = device_count * price_per_device
    return round(total_price, 2)


def format_payment_notification_message(payment, client=None) -> str:
    from datetime import datetime
    import pytz
    
    CAMBODIA_TZ = pytz.timezone('Asia/Phnom_Penh')
    
    verified_at = payment.verified_at
    if verified_at and verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=pytz.UTC).astimezone(CAMBODIA_TZ)
    elif verified_at:
        verified_at = verified_at.astimezone(CAMBODIA_TZ)
    
    timestamp_str = verified_at.strftime("%d/%m/%Y %H:%M:%S") if verified_at else "Unknown"
    
    message = (
        "✅ <b>Payment Received</b>\n"
        f"<b>Room:</b> {payment.room_number}\n"
        f"<b>Amount:</b> {payment.amount} {payment.currency}💵💵\n"
        f"<b>Time:</b> {timestamp_str}\n"
    )
    
    if payment.transaction_reference:
        message += f"<b>Reference:</b> {payment.transaction_reference}\n"
    
    if payment.bill_number:
        message += f"<b>Bill:</b> {payment.bill_number}\n"
    
    if payment.bakong_transaction_hash:
        message += f"<b>Hash:</b> {payment.bakong_transaction_hash[:16]}...\n"
    
    return message
