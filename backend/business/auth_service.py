import os
from datetime import datetime

from fastapi import HTTPException, status
from itsdangerous import BadSignature, SignatureExpired

from backend.core.config import SESSION_COOKIE_MAX_AGE, serializer
from backend.core.security import record_login_attempt, validate_login_attempt

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
CAMBODIA_TZ = None

try:
    import pytz
    CAMBODIA_TZ = pytz.timezone("Asia/Phnom_Penh")
except Exception:
    CAMBODIA_TZ = None


def create_session_payload(username: str) -> dict:
    timestamp = datetime.now(CAMBODIA_TZ) if CAMBODIA_TZ else datetime.now()
    return {
        "username": username,
        "timestamp": timestamp.isoformat(),
    }


def validate_session_cookie(session_cookie: str | None) -> dict:
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        return serializer.loads(session_cookie, max_age=SESSION_COOKIE_MAX_AGE)
    except SignatureExpired:
        raise HTTPException(status_code=401, detail="Session expired")
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid session")


def is_session_valid(session_cookie: str | None) -> bool:
    if not session_cookie:
        return False

    try:
        serializer.loads(session_cookie, max_age=SESSION_COOKIE_MAX_AGE)
        return True
    except (SignatureExpired, BadSignature):
        return False


def authenticate_admin(username: str, password: str) -> dict:
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        raise HTTPException(status_code=500, detail="Admin credentials not configured")

    validate_login_attempt(username)

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        record_login_attempt(username, success=True)
        return create_session_payload(username)

    record_login_attempt(username, success=False)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password",
    )
