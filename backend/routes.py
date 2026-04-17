from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from datetime import date, timedelta, datetime
import calendar
import os
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from backend.database import get_db
from backend.models import Client
from backend.security import (
    validate_mac_address, validate_room_number, validate_area, validate_ssid,
    validate_login_attempt, record_login_attempt, sanitize_string
)

router = APIRouter()

# Load credentials and secrets from environment variables
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# Session serializer
serializer = URLSafeTimedSerializer(SECRET_KEY)
SESSION_COOKIE_MAX_AGE = 8 * 60 * 60  # 8 hours in seconds


class ClientCreate(BaseModel):
    room_number: str
    area: str
    ssid: str = None
    mac: str
    due_date: date
    
    @field_validator('room_number')
    @classmethod
    def validate_room_num(cls, v):
        if not validate_room_number(v):
            raise ValueError('Room number must be 1-20 alphanumeric characters (-, allowed)')
        return v
    
    @field_validator('area')
    @classmethod
    def validate_area_field(cls, v):
        if not validate_area(v):
            raise ValueError('Area must be 1-100 alphanumeric characters')
        return v
    
    @field_validator('mac')
    @classmethod
    def validate_mac_field(cls, v):
        if not validate_mac_address(v):
            raise ValueError('MAC must be in format XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX')
        return v
    
    @field_validator('ssid')
    @classmethod
    def validate_ssid_field(cls, v):
        # Normalize: empty string stays empty, None stays None
        if isinstance(v, str) and len(v.strip()) == 0:
            return ""
        if v and not validate_ssid(v):
            raise ValueError('SSID must be 32 characters or less')
        return v


class ClientUpdate(BaseModel):
    room_number: str = None
    area: str = None
    ssid: str = None
    due_date: date = None
    last_payment: date = None
    
    @field_validator('room_number')
    @classmethod
    def validate_room_num(cls, v):
        if v and not validate_room_number(v):
            raise ValueError('Room number must be 1-20 alphanumeric characters')
        return v
    
    @field_validator('area')
    @classmethod
    def validate_area_field(cls, v):
        if v and not validate_area(v):
            raise ValueError('Area must be 1-100 alphanumeric characters')
        return v
    
    @field_validator('ssid')
    @classmethod
    def validate_ssid_field(cls, v):
        # Normalize: empty string stays empty, None stays None
        if isinstance(v, str) and len(v.strip()) == 0:
            return ""
        if v and not validate_ssid(v):
            raise ValueError('SSID must be 32 characters or less')
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


def verify_admin(username: str, password: str) -> bool:
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD


def get_next_monthly_due_date(current_due: date) -> date:
    """Calculate next month's due date from today, keeping the same day of month"""
    today = date.today()
    due_day = current_due.day
    
    # Start with next month
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1)
    else:
        next_month = today.replace(month=today.month + 1)
    
    # Handle day overflow (e.g., Jan 31 -> Feb 31 doesn't exist)
    max_day = calendar.monthrange(next_month.year, next_month.month)[1]
    due_day = min(due_day, max_day)
    
    return next_month.replace(day=due_day)


@router.post("/login")
def login(request: LoginRequest, response: Response):
    # Rate limiting check
    validate_login_attempt(request.username)
    
    # Security: Use constant-time comparison to prevent timing attacks
    username_match = request.username == ADMIN_USERNAME
    password_match = request.password == ADMIN_PASSWORD
    
    if username_match and password_match:
        record_login_attempt(request.username, success=True)
        
        # Create signed session token with username and timestamp
        session_data = {
            "username": request.username,
            "timestamp": datetime.utcnow().isoformat()
        }
        token = serializer.dumps(session_data)
        
        # Set HttpOnly cookie (not accessible from JavaScript)
        response.set_cookie(
            key="session",
            value=token,
            max_age=SESSION_COOKIE_MAX_AGE,
            httponly=True,
            secure=os.getenv("ENVIRONMENT", "development") == "production",
            samesite="Lax"
        )
        
        return {"status": "success", "message": "Login successful"}
    
    # Record failed attempt
    record_login_attempt(request.username, success=False)
    
    # Generic error message (don't reveal if username exists)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password"
    )


@router.get("/auth/check")
def check_auth(request: Request):
    """Validate session cookie and return authentication status"""
    session_cookie = request.cookies.get("session")
    
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        session_data = serializer.loads(session_cookie, max_age=SESSION_COOKIE_MAX_AGE)
        return {
            "status": "authenticated",
            "username": session_data.get("username")
        }
    except SignatureExpired:
        raise HTTPException(status_code=401, detail="Session expired")
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid session")


@router.post("/logout")
def logout(response: Response):
    """Clear session cookie and logout"""
    response.delete_cookie("session")
    return {"status": "success", "message": "Logged out"}


@router.get("/clients")
def list_clients(search: str = Query(None), db: Session = Depends(get_db)):
    query = db.query(Client)
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            (Client.room_number.ilike(search_term)) |
            (Client.area.ilike(search_term)) |
            (Client.ssid.ilike(search_term))
        )
    
    clients = query.all()
    return clients


@router.post("/clients")
def create_client(client: ClientCreate, db: Session = Depends(get_db)):
    existing = db.query(Client).filter(Client.mac == client.mac).first()
    if existing:
        raise HTTPException(status_code=400, detail="MAC address already exists")
    
    new_client = Client(
        room_number=client.room_number,
        area=client.area,
        ssid=client.ssid,
        mac=client.mac,
        due_date=client.due_date
    )
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    return new_client


@router.get("/clients/{mac}")
def get_client(mac: str, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.mac == mac).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/clients/{mac}")
def update_client(mac: str, update_data: ClientUpdate, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.mac == mac).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if update_data.room_number:
        client.room_number = update_data.room_number
    if update_data.area:
        client.area = update_data.area
    if update_data.ssid:
        client.ssid = update_data.ssid
    if update_data.due_date:
        client.due_date = update_data.due_date
    if update_data.last_payment is not None:
        if client.last_payment != update_data.last_payment:
            client.last_payment = update_data.last_payment
            # Auto-advance due date to next month when payment is marked
            client.due_date = get_next_monthly_due_date(client.due_date)
    
    db.commit()
    db.refresh(client)
    return client


@router.delete("/clients/{mac}")
def delete_client(mac: str, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.mac == mac).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    db.delete(client)
    db.commit()
    return {"status": "deleted", "mac": mac}


@router.post("/send-alert")
def send_alert(db: Session = Depends(get_db)):
    """Send payment alert via Telegram immediately (admin only)"""
    from backend.services import get_overdue_clients, get_due_soon_clients, get_active_clients, format_alert_message
    from backend.notify import send_telegram_message
    
    try:
        overdue = get_overdue_clients(db)
        due_soon = get_due_soon_clients(db)
        active = get_active_clients(db)
        
        message = format_alert_message(overdue, due_soon, active)
        success = send_telegram_message(message)
        
        if success:
            return {"status": "success", "message": "Alert sent successfully"}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to send Telegram message"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error sending alert: {str(e)}"
        )
