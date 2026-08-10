from sqlalchemy.orm import Session

from backend.infrastructure.models import Client, Payment


def get_clients_query(db: Session):
    return db.query(Client)


def search_clients(db: Session, search: str = None):
    query = get_clients_query(db)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            (Client.room_number.ilike(search_term)) |
            (Client.area.ilike(search_term)) |
            (Client.ssid.ilike(search_term))
        )

    return query.all()


def get_client_by_mac(db: Session, mac: str):
    return db.query(Client).filter(Client.mac == mac).first()


def create_client(db: Session, room_number: str, area: str, ssid: str, mac: str, due_day: int):
    client = Client(
        room_number=room_number,
        area=area,
        ssid=ssid,
        mac=mac,
        due_day=due_day,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def delete_client(db: Session, client):
    db.query(Payment).filter(Payment.client_id == client.id).delete(synchronize_session=False)
    db.delete(client)
    db.commit()
    return {"status": "deleted", "mac": client.mac}
