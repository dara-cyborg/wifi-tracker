from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from backend.business.alert_service import send_alert_service
from backend.business.auth_service import authenticate_admin, is_session_valid, validate_session_cookie
from backend.business.client_service import (
    create_client_service,
    delete_client_service,
    get_client_by_mac_service,
    list_clients,
    update_client_service,
)
from backend.core.config import SESSION_COOKIE_MAX_AGE, serializer
from backend.db.session import get_db
from backend.core.security import limiter

router = APIRouter()


class LoginRequest:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password


@router.post("/admin/login")
@limiter.limit("10/minute")
def login(request: Request, login_request: dict, response: Response):
    payload = authenticate_admin(login_request["username"], login_request["password"])
    token = serializer.dumps(payload)

    response.set_cookie(
        key="session",
        value=token,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        secure=request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https",
        samesite="Lax",
    )
    return {"status": "success", "message": "Login successful"}


@router.get("/admin/auth/check")
@limiter.limit("60/minute")
def check_auth(request: Request):
    return {"authenticated": is_session_valid(request.cookies.get("session"))}


@router.post("/admin/logout")
@limiter.limit("60/minute")
def logout(request: Request, response: Response):
    response.delete_cookie("session")
    return {"status": "success", "message": "Logged out"}


@router.get("/admin/clients")
@limiter.limit("60/minute")
def list_clients_endpoint(request: Request, search: str = Query(None), db: Session = Depends(get_db)):
    return list_clients(db, search)


@router.post("/admin/clients")
@limiter.limit("30/minute")
def create_client_endpoint(request: Request, client: dict, db: Session = Depends(get_db)):
    return create_client_service(db, type("ClientData", (), client)())


@router.get("/admin/clients/{mac}")
@limiter.limit("60/minute")
def get_client_endpoint(request: Request, mac: str, db: Session = Depends(get_db)):
    return get_client_by_mac_service(db, mac)


@router.put("/admin/clients/{mac}")
@limiter.limit("30/minute")
def update_client_endpoint(request: Request, mac: str, update_data: dict, db: Session = Depends(get_db)):
    return update_client_service(db, mac, type("UpdateData", (), update_data)())


@router.delete("/admin/clients/{mac}")
@limiter.limit("30/minute")
def delete_client_endpoint(request: Request, mac: str, db: Session = Depends(get_db)):
    return delete_client_service(db, mac)


@router.post("/admin/send-alert")
@limiter.limit("5/minute")
def send_alert(request: Request, db: Session = Depends(get_db)):
    try:
        return send_alert_service(db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending alert: {str(e)}")
