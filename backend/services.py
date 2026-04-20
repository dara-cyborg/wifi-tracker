from datetime import date
from sqlalchemy.orm import Session
from backend.models import Client
import calendar
import os


def get_current_month_due_date(due_day: int) -> date:
    """Get the due date for the current month based on due_day"""
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


def count_unique_devices_in_room(room_number: str, db: Session) -> int:
    """
    Count the number of unique devices (by MAC address) in a room.
    
    Args:
        room_number: The room number to count devices for
        db: Database session
        
    Returns:
        The count of unique MAC addresses in the room
    """
    count = db.query(Client).filter(Client.room_number == room_number).count()
    return count


def calculate_room_price(room_number: str, db: Session, price_per_device: float = None) -> float:
    """
    Calculate the total price for a room based on unique devices.
    Each unique device (MAC address) costs price_per_device per month.
    
    Args:
        room_number: The room number to calculate price for
        db: Database session
        price_per_device: Price per device per month (default: from PRICE_PER_DEVICE_PER_MONTH env var, fallback to $2.50)
        
    Returns:
        Total price in USD for all devices in the room
    """
    if price_per_device is None:
        price_per_device = float(os.getenv("PRICE_PER_DEVICE_PER_MONTH", "2.5"))
    
    device_count = count_unique_devices_in_room(room_number, db)
    total_price = device_count * price_per_device
    return round(total_price, 2)
