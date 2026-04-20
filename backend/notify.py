import os
import requests
import logging

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def send_telegram_message(message: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def send_payment_notification(payment, client=None) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Payment notification skipped: Telegram credentials not configured")
        return False
    
    try:
        from backend.services import format_payment_notification_message
        
        message = format_payment_notification_message(payment, client)
        success = send_telegram_message(message)
        
        if success:
            logger.info(f"Payment notification sent for payment_id={payment.id}, room={payment.room_number}")
        else:
            logger.error(f"Failed to send payment notification for payment_id={payment.id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error sending payment notification: {e}", exc_info=True)
        return False
