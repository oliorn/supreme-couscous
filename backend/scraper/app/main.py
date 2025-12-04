from fastapi import FastAPI, Query, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
import json

from app.scraper import scrape_company
from app.database import SessionLocal, engine  
from .models import Company, EmailSent, Base
from .email_service import get_email_service

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Virkum Company Scraper & Email API")

# --- CORS so React (localhost:3000) can talk to FastAPI ---
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class CompanyOut(BaseModel):
    CompanyName: str
    CompanyDescription: str | None = None
    CompanyInfo: str | None = None

    class Config:
        orm_mode = True

class EmailRequest(BaseModel):
    to: EmailStr
    subject: str
    content: str
    company_name: Optional[str] = None
    company_description: Optional[str] = None
    company_info: Optional[str] = None
    html_content: Optional[str] = None

class EmailResponse(BaseModel):
    success: bool
    message: str
    recipient: str
    subject: str
    error: Optional[str] = None

# DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/companies", response_model=List[CompanyOut])
def list_companies(db: Session = Depends(get_db)):
    # Use DISTINCT to get unique companies by name
    result = db.execute(
        text(
            """
            SELECT DISTINCT ON ("CompanyName") 
                   "CompanyName", "CompanyDescription", "CompanyInfo"
            FROM "Companies"
            ORDER BY "CompanyName"
            """
        )
    )
    rows = result.mappings().all()

    # Map rows to plain dicts that match CompanyOut
    companies = [
        {
            "CompanyName": row["CompanyName"],
            "CompanyDescription": row["CompanyDescription"],
            "CompanyInfo": row["CompanyInfo"],
        }
        for row in rows
    ]

    return companies

@app.get("/")
def root():
    return {"message": "✅ Scraper service is running."}

@app.get("/scrape")
def scrape(
    url: str = Query(..., description="Public website URL"),
    db: Session = Depends(get_db),
):
    # Get scraped data
    data = scrape_company(url)
    if "error" in data:
        raise HTTPException(status_code=400, detail=data["error"])

    # Map to database columns
    name = data.get("company_name") or ""
    descr = data.get("company_description") or ""
    info = data.get("company_information") or ""

    saved = False
    error = None
    action = "created"
    
    try:
        # Check if company already exists
        existing = db.execute(
            text(
                """
                SELECT "CompanyName" FROM "Companies" 
                WHERE "CompanyName" = :name
                """
            ),
            {"name": name},
        ).fetchone()

        if existing:
            # Update existing company instead of creating new one
            db.execute(
                text(
                    """
                    UPDATE "Companies" 
                    SET "CompanyDescription" = :descr, "CompanyInfo" = :info
                    WHERE "CompanyName" = :name
                    """
                ),
                {"name": name, "descr": descr, "info": info},
            )
            action = "updated"
        else:
            # Create new company
            db.execute(
                text(
                    """
                    INSERT INTO "Companies" ("CompanyName", "CompanyDescription", "CompanyInfo")
                    VALUES (:name, :descr, :info)
                    """
                ),
                {"name": name, "descr": descr, "info": info},
            )
            action = "created"
        
        db.commit()
        saved = True
    except Exception as e:
        error = str(e)

    return {
        "saved": saved,
        "action": action,
        "db_error": error,
        "scraped": data,
    }

@app.delete("/cleanup-duplicates")
def cleanup_duplicates(db: Session = Depends(get_db)):
    """
    Remove duplicate companies based on CompanyName
    """
    try:
        result = db.execute(
            text("""
                DELETE FROM "Companies" 
                WHERE ctid NOT IN (
                    SELECT MIN(ctid) 
                    FROM "Companies" 
                    GROUP BY "CompanyName"
                )
            """)
        )
        db.commit()
        
        return {"message": f"Removed {result.rowcount} duplicate company/companies"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error removing duplicates: {str(e)}")

# NEW: Email sending endpoint
@app.post("/send-email", response_model=EmailResponse)
async def send_email(
    email_request: EmailRequest,
    db: Session = Depends(get_db)
):
    """
    Send an email using the configured email service
    """
    # Get email service
    email_service = get_email_service()
    
    # Prepare company info if provided
    company_info = None
    if email_request.company_name:
        company_info = {
            "name": email_request.company_name,
            "description": email_request.company_description or "",
            "info": email_request.company_info or ""
        }
    
    # Send email
    result = email_service.send_email(
        to_email=email_request.to,
        subject=email_request.subject,
        content=email_request.content,
        html_content=email_request.html_content,
        company_info=company_info
    )
    
    # Log the email in database
    try:
        # Find company ID if company name is provided
        company_id = None
        if email_request.company_name:
            company = db.execute(
                text('SELECT id FROM "Companies" WHERE "CompanyName" = :name'),
                {"name": email_request.company_name}
            ).fetchone()
            if company:
                company_id = company[0]
        
        # Insert email record
        email_record = EmailSent(
            company_id=company_id,
            recipient=email_request.to,
            subject=email_request.subject,
            content=email_request.content,
            status="sent" if result["success"] else "failed",
            error_message=None if result["success"] else result.get("error")
        )
        db.add(email_record)
        db.commit()
        
    except Exception as e:
        # Don't fail the whole request if logging fails
        print(f"Failed to log email: {e}")
    
    # Return result
    if result["success"]:
        return EmailResponse(
            success=True,
            message=result["message"],
            recipient=result["recipient"],
            subject=result["subject"]
        )
    else:
        return EmailResponse(
            success=False,
            message="Failed to send email",
            recipient=result.get("recipient", email_request.to),
            subject=email_request.subject,
            error=result.get("error", "Unknown error")
        )

# NEW: Get email sending history
@app.get("/email-history")
def get_email_history(
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get history of sent emails
    """
    try:
        emails = db.query(EmailSent).order_by(EmailSent.sent_at.desc()).limit(limit).all()
        
        return [
            {
                "id": email.id,
                "recipient": email.recipient,
                "subject": email.subject,
                "sent_at": email.sent_at.isoformat() if email.sent_at else None,
                "status": email.status,
                "company_id": email.company_id
            }
            for email in emails
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching email history: {str(e)}")

# NEW: Check email service status
@app.get("/email-service/status")
def check_email_service():
    """
    Check if email service is properly configured
    """
    email_service = get_email_service()
    
    # Simple check based on type
    if hasattr(email_service, 'api_key') and not email_service.api_key:
        return {
            "configured": False,
            "service": "SendGrid",
            "message": "SendGrid API key not configured"
        }
    elif hasattr(email_service, 'smtp_username') and not email_service.smtp_username:
        return {
            "configured": False,
            "service": "SMTP",
            "message": "SMTP credentials not configured"
        }
    else:
        return {
            "configured": True,
            "service": "SendGrid" if hasattr(email_service, 'api_key') else "SMTP",
            "message": "Email service is configured and ready"
        }
    
@app.get("/tests")
def list_tests(
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    try:
        sql = text("""
            SELECT
                test_id,
                companies,
                num_emails,
                concurrency_level,
                started_at,
                finished_at,
                total_requests,
                avg_reply_grade
            FROM tests
            ORDER BY test_id DESC
            LIMIT :limit
        """)

        rows = db.execute(sql, {"limit": limit}).mappings().all()

        def parse_companies(val):
            # Ensure companies is a Python list, regardless of JSONB/text
            try:
                if val is None:
                    return []
                if isinstance(val, (list, dict)):
                    return val
                return json.loads(val)
            except Exception:
                # Fallback: return as-is if parsing fails
                return val

        return [
            {
                "test_id": row["test_id"],
                "companies": parse_companies(row["companies"]),
                "num_emails": row["num_emails"],
                "concurrency_level": row["concurrency_level"],
                "started_at": row["started_at"],
                "finished_at": row["finished_at"],
                "total_requests": row["total_requests"],
                "avg_reply_grade": row["avg_reply_grade"],
            }
            for row in rows
        ]

    except Exception as e:
        import traceback
        print("[ERROR] /tests handler exception:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))