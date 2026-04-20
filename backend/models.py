from sqlalchemy import Column, Integer, String, Date, DateTime, Float, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import pytz

CAMBODIA_TZ = pytz.timezone('Asia/Phnom_Penh')

Base = declarative_base()


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    room_number = Column(String, index=True, nullable=False)
    area = Column(String, nullable=False)
    ssid = Column(String)
    mac = Column(String, unique=True, index=True, nullable=False)
    due_day = Column(Integer, nullable=False)
    last_payment = Column(Date)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(CAMBODIA_TZ))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(CAMBODIA_TZ), onupdate=lambda: datetime.now(CAMBODIA_TZ))
    
    payments = relationship("Payment", back_populates="client")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    room_number = Column(String, nullable=False, index=True)
    
    qr_string = Column(Text, nullable=False)
    qr_md5_hash = Column(String(32), nullable=False, unique=True, index=True)
    
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    
    bill_number = Column(String, nullable=True)
    transaction_reference = Column(String, nullable=True)
    bakong_transaction_hash = Column(String, nullable=True, index=True)
    
    payment_status = Column(
        String(20),
        default="PENDING",
        nullable=False,
        index=True
    )
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(CAMBODIA_TZ), index=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    client = relationship("Client", back_populates="payments")
