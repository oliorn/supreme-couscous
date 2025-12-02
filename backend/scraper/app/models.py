from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from .database import Base

class Company(Base):
    __tablename__ = "Companies"  # taflan í google cloud

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    url = Column(String)
    description = Column(String)


class EmailSent(Base):
    __tablename__ = "emails_sent"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=True)
    recipient = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="sent")
    error_message = Column(String, nullable=True)