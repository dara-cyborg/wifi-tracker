from fastapi import HTTPException

from backend.business.client_service import (
    get_active_clients,
    get_not_set_clients,
    get_overdue_clients,
)
from backend.infrastructure.notify import send_telegram_message


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
            message += f"• បន្ទល់លេខ {client.room_number} - {client.area}\n"

    return message


def build_alert_summary(db):
    overdue = get_overdue_clients(db)
    active = get_active_clients(db)
    not_set = get_not_set_clients(db)
    return {
        "overdue": overdue,
        "active": active,
        "not_set": not_set,
        "message": format_alert_message(overdue, active, not_set),
    }


def send_alert_service(db):
    summary = build_alert_summary(db)
    success = send_telegram_message(summary["message"])

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send Telegram message")

    return {"status": "success", "message": "Alert sent successfully"}
