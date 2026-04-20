from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from datetime import date, datetime, timedelta, timezone
import os
import logging
import pytz
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from backend.database import get_db
from backend.models import Client, Payment
from backend.security import (
    validate_mac_address, validate_room_number, validate_area, validate_ssid,
    validate_login_attempt, record_login_attempt, limiter
)

logger = logging.getLogger(__name__)
router = APIRouter()

CAMBODIA_TZ = pytz.timezone('Asia/Phnom_Penh')

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable not set")

serializer = URLSafeTimedSerializer(SECRET_KEY)
SESSION_COOKIE_MAX_AGE = 8 * 60 * 60


def ensure_aware_datetime(dt: datetime) -> datetime:
    """SQLite returns naive UTC; convert to Cambodia timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone(CAMBODIA_TZ)
    return dt.astimezone(CAMBODIA_TZ)


class ClientCreate(BaseModel):
    room_number: str
    area: str
    ssid: str = None
    mac: str
    due_day: int
    
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
        if isinstance(v, str) and len(v.strip()) == 0:
            return ""
        if v and not validate_ssid(v):
            raise ValueError('SSID must be 32 characters or less')
        return v
    
    @field_validator('due_day')
    @classmethod
    def validate_due_day(cls, v):
        if not isinstance(v, int) or v < 1 or v > 31:
            raise ValueError('Due day must be between 1 and 31')
        return v


class ClientUpdate(BaseModel):
    room_number: str = None
    area: str = None
    ssid: str = None
    due_day: int = None
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
        if isinstance(v, str) and len(v.strip()) == 0:
            return ""
        if v and not validate_ssid(v):
            raise ValueError('SSID must be 32 characters or less')
        return v
    
    @field_validator('due_day')
    @classmethod
    def validate_due_day(cls, v):
        if v is not None and (not isinstance(v, int) or v < 1 or v > 31):
            raise ValueError('Due day must be between 1 and 31')
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class PaymentVerifyRequest(BaseModel):
    payment_id: int


def get_current_user(request: Request) -> dict:
    """Validate session and return user data; raises 401 if invalid."""
    session_cookie = request.cookies.get("session")
    
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        session_data = serializer.loads(session_cookie, max_age=SESSION_COOKIE_MAX_AGE)
        return session_data
    except SignatureExpired:
        raise HTTPException(status_code=401, detail="Session expired")
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid session")


@limiter.limit("10/minute")
@router.post("/admin/login")
def login(request: Request, login_request: LoginRequest, response: Response):
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        raise HTTPException(
            status_code=500,
            detail="Admin credentials not configured"
        )
    
    validate_login_attempt(login_request.username)
    
    username_match = login_request.username == ADMIN_USERNAME
    password_match = login_request.password == ADMIN_PASSWORD
    
    if username_match and password_match:
        record_login_attempt(login_request.username, success=True)
        
        session_data = {
            "username": login_request.username,
            "timestamp": datetime.now(CAMBODIA_TZ).isoformat()
        }
        token = serializer.dumps(session_data)
        
        response.set_cookie(
            key="session",
            value=token,
            max_age=SESSION_COOKIE_MAX_AGE,
            httponly=True,
            secure=os.getenv("ENVIRONMENT", "development") == "production",
            samesite="Lax"
        )
        
        return {"status": "success", "message": "Login successful"}
    
    record_login_attempt(login_request.username, success=False)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password"
    )

@limiter.limit("60/minute")
@router.get("/admin/auth/check")
def check_auth(request: Request):
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

@limiter.limit("60/minute")
@router.post("/admin/logout")
def logout(request: Request, response: Response):
    response.delete_cookie("session")
    return {"status": "success", "message": "Logged out"}

@limiter.limit("60/minute")
@router.get("/admin/clients")
def list_clients(request: Request, search: str = Query(None), db: Session = Depends(get_db)):
    from backend.services import get_client_status
    
    query = db.query(Client)
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            (Client.room_number.ilike(search_term)) |
            (Client.area.ilike(search_term)) |
            (Client.ssid.ilike(search_term))
        )
    
    clients = query.all()
    
    result = []
    for client in clients:
        client_dict = {
            "id": client.id,
            "room_number": client.room_number,
            "area": client.area,
            "ssid": client.ssid,
            "mac": client.mac,
            "due_day": client.due_day,
            "last_payment": client.last_payment,
            "status": get_client_status(client)
        }
        result.append(client_dict)
    
    return result


@limiter.limit("30/minute")
@router.post("/admin/clients")
def create_client(request: Request, client: ClientCreate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(Client).filter(Client.mac == client.mac).first()
    if existing:
        raise HTTPException(status_code=400, detail="MAC address already exists")
    
    new_client = Client(
        room_number=client.room_number,
        area=client.area,
        ssid=client.ssid,
        mac=client.mac,
        due_day=client.due_day
    )
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    return new_client


@limiter.limit("60/minute")
@router.get("/admin/clients/{mac}")
def get_client(request: Request, mac: str, db: Session = Depends(get_db)):
    from backend.services import get_client_status
    
    client = db.query(Client).filter(Client.mac == mac).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    client_dict = {
        "id": client.id,
        "room_number": client.room_number,
        "area": client.area,
        "ssid": client.ssid,
        "mac": client.mac,
        "due_day": client.due_day,
        "last_payment": client.last_payment,
        "status": get_client_status(client)
    }
    return client_dict

@limiter.limit("30/minute")
@router.put("/admin/clients/{mac}")
def update_client(request: Request, mac: str, update_data: ClientUpdate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.mac == mac).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if update_data.room_number:
        client.room_number = update_data.room_number
    if update_data.area:
        client.area = update_data.area
    if update_data.ssid:
        client.ssid = update_data.ssid
    if update_data.due_day:
        client.due_day = update_data.due_day
    if update_data.last_payment is not None:
        client.last_payment = update_data.last_payment
    
    db.commit()
    db.refresh(client)
    return client

@limiter.limit("30/minute")
@router.delete("/admin/clients/{mac}")
def delete_client(request: Request, mac: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.mac == mac).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    db.delete(client)
    db.commit()
    return {"status": "deleted", "mac": mac}

@limiter.limit("5/minute")
@router.post("/admin/send-alert")
def send_alert(request: Request, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.services import get_overdue_clients, get_active_clients, get_not_set_clients, format_alert_message
    from backend.notify import send_telegram_message
    
    try:
        overdue = get_overdue_clients(db)
        active = get_active_clients(db)
        not_set = get_not_set_clients(db)
        
        message = format_alert_message(overdue, active, not_set)
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

@limiter.limit("60/minute")
@router.post("/customer/payment/generate-qr/{room_number}")
def generate_payment_qr(room_number: str, request: Request, db: Session = Depends(get_db)):
    try:
        from backend.bakong import BakongService, BakongConfig
        
        client = db.query(Client).filter(Client.room_number == room_number).first()
        if not client:
            raise HTTPException(status_code=404, detail=f"Room {room_number} not found")
        
        all_pending = db.query(Payment).filter(
            Payment.client_id == client.id,
            Payment.payment_status == "PENDING"
        ).all()
        
        now = datetime.now(CAMBODIA_TZ)
        existing_payment = None
        for payment in all_pending:
            payment_expires_at = ensure_aware_datetime(payment.expires_at)
            if payment_expires_at > now:
                existing_payment = payment
                break
        
        if existing_payment:
            
            config = BakongConfig()
            service = BakongService(config)
            qr_image_data = service.generate_qr_image(existing_payment.qr_string)
            
            if not qr_image_data:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate QR image"
                )
            
            return {
                "payment_id": existing_payment.id,
                "room_number": existing_payment.room_number,
                "amount": existing_payment.amount,
                "currency": existing_payment.currency,
                "qr_image": qr_image_data,
                "expires_at": ensure_aware_datetime(existing_payment.expires_at).isoformat(),
                "status": existing_payment.payment_status
            }
        
        config = BakongConfig()
        service = BakongService(config)
        
        from datetime import date as dt_date
        bill_ref = f"Room{room_number}-{dt_date.today().isoformat()}"
        
        from backend.services import calculate_room_price
        amount = calculate_room_price(room_number, db)
        currency = "USD"
        
        qr_result = service.generate_qr(
            amount=amount,
            bill_number=bill_ref,
            description=f"WiFi Payment for Room {room_number}"
        )
        
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        
        payment = Payment(
            client_id=client.id,
            room_number=room_number,
            qr_string=qr_result["qr_string"],
            qr_md5_hash=qr_result["qr_md5"],
            amount=amount,
            currency=currency,
            bill_number=bill_ref,
            transaction_reference=f"PAY-{room_number}-{datetime.now(CAMBODIA_TZ).timestamp()}",
            payment_status="PENDING",
            expires_at=expires_at
        )
        
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        qr_image_data = service.generate_qr_image(qr_result["qr_string"])
        
        if not qr_image_data:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate QR image"
            )
        
        aware = ensure_aware_datetime(payment.expires_at)
        
        return {
            "payment_id": payment.id,
            "room_number": payment.room_number,
            "amount": payment.amount,
            "currency": payment.currency,
            "qr_image": qr_image_data,
            "expires_at": aware.isoformat(),
            "status": payment.payment_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate payment QR: {str(e)}"
        )


@limiter.limit("60/minute")
@router.get("/customer/pricing/{room_number}")
def get_room_pricing(room_number: str, request: Request, db: Session = Depends(get_db)):
    try:
        client = db.query(Client).filter(Client.room_number == room_number).first()
        if not client:
            raise HTTPException(status_code=404, detail=f"Room {room_number} not found")
        
        from backend.services import calculate_room_price, count_unique_devices_in_room
        import os
        
        device_count = count_unique_devices_in_room(room_number, db)
        total_price = calculate_room_price(room_number, db)
        price_per_device = float(os.getenv("PRICE_PER_DEVICE_PER_MONTH", "2.5"))
        
        return {
            "room_number": room_number,
            "device_count": device_count,
            "price_per_device": price_per_device,
            "currency": "USD",
            "total_price": total_price
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pricing: {str(e)}"
        )


@limiter.limit("25/minute")
@router.post("/customer/payment/verify")
def verify_payment(verify_request: PaymentVerifyRequest, request: Request, db: Session = Depends(get_db)):
    try:
        from backend.bakong import BakongService, BakongConfig
        
        payment = db.query(Payment).filter(Payment.id == verify_request.payment_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        if payment.payment_status == "VERIFIED":
            return {
                "payment_id": payment.id,
                "verified": True,
                "status": "VERIFIED",
                "message": "Payment already verified",
                "timestamp": datetime.now(CAMBODIA_TZ).isoformat()
            }
        
        payment_expires_at = ensure_aware_datetime(payment.expires_at)
        if payment_expires_at < datetime.now(CAMBODIA_TZ):
            if payment.payment_status != "EXPIRED":
                payment.payment_status = "EXPIRED"
                db.commit()
            
            return {
                "payment_id": payment.id,
                "verified": False,
                "status": "EXPIRED",
                "message": "Payment QR has expired. Generate a new one.",
                "timestamp": datetime.now(CAMBODIA_TZ).isoformat()
            }
        
        config = BakongConfig()
        service = BakongService(config)
        result = service.verify_payment(payment.qr_md5_hash)
        
        if result["status"] == "PAID":
            payment.payment_status = "VERIFIED"
            payment.verified_at = datetime.now(CAMBODIA_TZ)
            
            if result["payment_data"]:
                payment.bakong_transaction_hash = result["payment_data"].get("hash")
            
            all_clients_in_room = db.query(Client).filter(Client.room_number == payment.room_number).all()
            for client in all_clients_in_room:
                client.last_payment = date.today()
            
            db.commit()
            
            # Send payment notification to Telegram
            from backend.notify import send_payment_notification
            send_payment_notification(payment)
            
            return {
                "payment_id": payment.id,
                "verified": True,
                "status": "VERIFIED",
                "message": "Payment verified successfully!",
                "timestamp": datetime.now(CAMBODIA_TZ).isoformat()
            }
        
        elif result["status"] == "UNPAID":
            return {
                "payment_id": payment.id,
                "verified": False,
                "status": "UNPAID",
                "message": "Payment not yet received. Please wait or try again.",
                "timestamp": datetime.now(CAMBODIA_TZ).isoformat()\
            }
        
        elif result["status"] == "NOT_FOUND":
            return {
                "payment_id": payment.id,
                "verified": False,
                "status": "PENDING",
                "message": "QR not yet recognized by Bakong. Please wait or generate a new QR.",
                "timestamp": datetime.now(CAMBODIA_TZ).isoformat()
            }
        
        else:
            raise HTTPException(
                status_code=503,
                detail=result.get("error", "Could not verify payment at this time. Please try again."),
                headers={"Retry-After": "5"}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail="Could not verify payment at this time. Please try again later."
        )