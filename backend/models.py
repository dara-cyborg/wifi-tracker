from sqlalchemy import Column, Integer, String, Date, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    room_number = Column(String, index=True, nullable=False)
    area = Column(String, nullable=False)
    ssid = Column(String)
    mac = Column(String, unique=True, index=True, nullable=False)
    due_day = Column(Integer, nullable=False)  # Day of month (1-31)
    last_payment = Column(Date)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
