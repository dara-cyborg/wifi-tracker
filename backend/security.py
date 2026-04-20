"""Security utilities for WiFi Tracker"""
import re
import os
from datetime import datetime, timedelta
from typing import Dict
from fastapi import HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

login_attempts: Dict[str, list] = {}
MAX_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOCKOUT_MINUTES = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15"))

def validate_mac_address(mac: str) -> bool:
    """Validate MAC address format: XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX"""
    pattern = r'^([0-9A-Fa-f]{2}[:\-]){5}([0-9A-Fa-f]{2})$'
    return bool(re.match(pattern, mac.strip()))

def validate_room_number(room: str) -> bool:
    """Validate room number: alphanumeric, 1-20 chars, no special chars"""
    pattern = r'^[a-zA-Z0-9\-]{1,20}$'
    return bool(re.match(pattern, room.strip()))

def validate_area(area: str) -> bool:
    """Validate area: alphanumeric and spaces, 1-100 chars"""
    pattern = r'^[a-zA-Z0-9\s\-]{1,100}$'
    return bool(re.match(pattern, area.strip()))

def validate_ssid(ssid: str) -> bool:
    """Validate SSID: any chars, max 32 chars (WiFi standard)"""
    if not ssid or len(ssid) == 0:
        return True  # SSID is optional
    return len(ssid.strip()) <= 32

def validate_login_attempt(username: str) -> None:
    """Check if user has exceeded login attempts"""
    now = datetime.now()
    
    if username not in login_attempts:
        login_attempts[username] = []
    
    login_attempts[username] = [
        attempt_time for attempt_time in login_attempts[username]
        if now - attempt_time < timedelta(minutes=LOCKOUT_MINUTES)
    ]
    
    if len(login_attempts[username]) >= MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {LOCKOUT_MINUTES} minutes."
        )

def record_login_attempt(username: str, success: bool = False) -> None:
    if success:
        if username in login_attempts:
            login_attempts[username] = []
    else:
        if username not in login_attempts:
            login_attempts[username] = []
        login_attempts[username].append(datetime.now())
