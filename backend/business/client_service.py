from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.infrastructure.repositories.client_repository import (
    create_client,
    delete_client,
    get_client_by_mac,
    search_clients,
)
from backend.infrastructure.models import Client


def get_client_status(client: Client) -> str:
    if not client.last_payment:
        return "Not set"

    today = date.today()
    if client.last_payment.year == today.year and client.last_payment.month == today.month:
        return "Active"

    return "overdue"


def serialize_client(client: Client) -> dict:
    return {
        "id": client.id,
        "room_number": client.room_number,
        "area": client.area,
        "ssid": client.ssid,
        "mac": client.mac,
        "due_day": client.due_day,
        "last_payment": client.last_payment,
        "status": get_client_status(client),
    }


def list_clients(db: Session, search: str = None):
    clients = search_clients(db, search)
    return [serialize_client(client) for client in clients]


def get_client_by_mac_service(db: Session, mac: str):
    client = get_client_by_mac(db, mac)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return serialize_client(client)


def create_client_service(db: Session, client_data):
    existing = get_client_by_mac(db, client_data.mac)
    if existing:
        raise HTTPException(status_code=400, detail="MAC address already exists")

    return create_client(
        db,
        room_number=client_data.room_number,
        area=client_data.area,
        ssid=client_data.ssid,
        mac=client_data.mac,
        due_day=client_data.due_day,
    )


def parse_date_value(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid last_payment date format. Use YYYY-MM-DD.")
    raise HTTPException(status_code=400, detail="Invalid last_payment type.")


def update_client_service(db: Session, mac: str, update_data):
    client = get_client_by_mac(db, mac)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if getattr(update_data, "room_number", None):
        client.room_number = update_data.room_number
    if getattr(update_data, "area", None):
        client.area = update_data.area
    if getattr(update_data, "ssid", None):
        client.ssid = update_data.ssid
    if getattr(update_data, "due_day", None) is not None:
        client.due_day = update_data.due_day
    if getattr(update_data, "last_payment", None) is not None:
        client.last_payment = parse_date_value(update_data.last_payment)

    db.commit()
    db.refresh(client)
    return client


def delete_client_service(db: Session, mac: str):
    client = get_client_by_mac(db, mac)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    try:
        return delete_client(db, client)
    except Exception:
        db.rollback()
        raise


def get_overdue_clients(db: Session):
    all_clients = search_clients(db)
    overdue = []
    for client in all_clients:
        status = get_client_status(client)
        if status != "Not set" and status != "Active":
            overdue.append((client, status))
    return overdue


def get_active_clients(db: Session):
    all_clients = search_clients(db)
    active = []
    for client in all_clients:
        if get_client_status(client) == "Active":
            active.append(client)
    return active


def get_not_set_clients(db: Session):
    all_clients = search_clients(db)
    not_set = []
    for client in all_clients:
        if get_client_status(client) == "Not set":
            not_set.append(client)
    return not_set
