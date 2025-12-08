from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Numeric
from datetime import datetime
from .database import Base
from sqlalchemy.sql import func

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

class EmailTestRun(Base):
    __tablename__ = "EmailTestRuns"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(Integer, nullable=True)   # má vera null 
    company_name = Column(String, nullable=False)

    scenario = Column(String, nullable=True)      # "Complaint" / "Ingredients question" etc.
    input_email = Column(Text, nullable=False)

    generated_subject = Column(String, nullable=True)
    generated_body = Column(Text, nullable=True)

    model_name = Column(String, nullable=True)    # t.d. "gpt-4.1-mini"
    latency_ms = Column(Integer, nullable=True)

    sent_ok = Column(Boolean, default=False)

    reply_grade = Column(Numeric, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ExpectedAnswer(Base):
    __tablename__ = "ExpectedAnswers"

    id = Column(Integer, primary_key=True, index=True)
    scenario = Column(Text, nullable=False)
    company_name = Column(String, nullable=False)
    expected_body = Column(Text, nullable=False)