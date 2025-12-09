from fastapi import FastAPI, Query, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
import json
import random  
import os

from app.scraper import scrape_company
from app.database import SessionLocal, engine
from .models import Company, EmailSent, Base, EmailTestRun
from .email_service import get_email_service
from .llm_service import generate_reply_with_openai, evaluate_with_openai_rubric
from .simulation_service import run_single_simulation, create_test_summary_from_run_ids


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

#  Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Virkum Company Scraper & Email API")

# --- CORS so React (localhost:3000) can talk to FastAPI ---
origins = [
    "https://virkum-respond-frontend-737530900569.europe-west2.run.app",    
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

class RunTestRequest(BaseModel):
    num_emails: int
    concurrency_level: int = 1
    to: EmailStr
    company_name: Optional[str] = None  # if None → random

class ManualGenerateRequest(BaseModel):
    company_name: str       # verður að velja company í UI
    to: EmailStr            # recipient (má nota sama og í Email Settings)
    input_email: str        # textinn úr textboxinu

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
                   id,
               "CompanyName",
               "CompanyDescription",
               "CompanyInfo"
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

@app.post("/manual-generate")
def manual_generate_email(
    body: ManualGenerateRequest,
    db: Session = Depends(get_db),
):
    """
    Tekur 'Mock Email to Respond To' frá UI, býr til svar með LLM,
    vistar í EmailTestRuns og býr til tests-row með num_emails=1.
    """
    input_email = body.input_email.strip()
    if not input_email:
        raise HTTPException(status_code=400, detail="input_email is empty")

    company_name = body.company_name

    # 1) Scenario: notum fyrstu línu (t.d. "Subject: ...")
    first_line = input_email.splitlines()[0].strip()
    scenario = first_line or "Manual scenario"

    # 2) LLM svar
    generated_subject, generated_body, model_name, llm_latency_ms = generate_reply_with_openai(
        company_name=company_name,
        input_email=input_email,
    )
    total_latency_ms = llm_latency_ms

    # 3) Búa til EmailTestRun
    test_run = EmailTestRun(
        company_name=company_name,
        scenario=scenario,
        input_email=input_email,
        generated_subject=generated_subject,
        generated_body=generated_body,
        model_name=model_name,
        latency_ms=total_latency_ms,
        sent_ok=False,   # við erum bara að generate-a, ekki senda raunpóst hér
    )

    # 4) LLM dómari – gefur einkunn
    try:
        grade, eval_latency_ms = evaluate_with_openai_rubric(
            company_name=company_name,
            scenario=scenario,
            input_email=input_email,
            generated_body=generated_body,
        )
        test_run.reply_grade = grade
    except Exception as e:
        print(f"LLM grading failed (manual_generate): {e}")

    db.add(test_run)
    db.commit()
    db.refresh(test_run)

    # 5) Búa til tests-row eins og þetta sé batch með einu email
    summary = create_test_summary_from_run_ids(
        db=db,
        run_ids=[test_run.id],
        concurrency_level=1,
    )

    return {
        "status": "ok",
        "test_run_id": test_run.id,
        "test_summary": summary,
        "generated_subject": generated_subject,
        "generated_body": generated_body,
        "grade": float(test_run.reply_grade) if test_run.reply_grade is not None else None,
    }



class SimulateRequest(BaseModel):
    company_name: Optional[str] = None
    to: EmailStr


@app.post("/simulate-email")
def simulate_email(
    body: SimulateRequest,
):
    """
    Wrapper around run_single_simulation for the UI.
    """
    test_run, total_latency_ms, llm_latency_ms = run_single_simulation(
        to_email=body.to,
        company_name=body.company_name,
    )

    send_message = "Simulation only – email was NOT actually sent."

    return {
        "status": "ok",
        "company_used": test_run.company_name,
        "latency_ms": total_latency_ms,
        "llm_latency_ms": llm_latency_ms,
        "sent_ok": test_run.sent_ok,
        "test_run_id": test_run.id,
        "preview": {
            "scenario": test_run.scenario,
            "input_email": test_run.input_email,
            "generated_subject": test_run.generated_subject,
            "generated_body": test_run.generated_body,
            "send_message": send_message,
            "reply_grade": float(test_run.reply_grade) if test_run.reply_grade is not None else None,
        },
    }


class EvaluateRequest(BaseModel):
    test_run_id: int

@app.post("/evaluate-test-run")
def evaluate_test_run(
    body: EvaluateRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Endurmetur eða metur test_run með LLM-dómara án ExpectedAnswer.
    """
    test_run = (
        db.query(EmailTestRun)
        .filter(EmailTestRun.id == body.test_run_id)
        .first()
    )
    if not test_run:
        raise HTTPException(status_code=404, detail="EmailTestRun not found")

    if not test_run.generated_body:
        raise HTTPException(
            status_code=400,
            detail="No generated_body to evaluate for this test_run",
        )

    # LLM-dómari án ExpectedAnswer
    grade, eval_latency_ms = evaluate_with_openai_rubric(
        company_name=test_run.company_name,
        scenario=test_run.scenario,
        input_email=test_run.input_email,
        generated_body=test_run.generated_body,
    )

    test_run.reply_grade = grade
    db.commit()
    db.refresh(test_run)

    return {
        "status": "ok",
        "test_run_id": test_run.id,
        "company_name": test_run.company_name,
        "scenario": test_run.scenario,
        "grade": float(grade),
        "evaluation_latency_ms": eval_latency_ms,
    }

import asyncio

@app.post("/run-simulated-test")
async def run_simulated_test(
    body: RunTestRequest,
    db: Session = Depends(get_db),
):
    if body.num_emails <= 0:
        raise HTTPException(status_code=400, detail="num_emails must be > 0")
    if body.concurrency_level <= 0:
        raise HTTPException(status_code=400, detail="concurrency_level must be > 0")

    semaphore = asyncio.Semaphore(body.concurrency_level)

    async def run_one():
        async with semaphore:
            test_run, _, _ = await asyncio.to_thread(
                run_single_simulation,
                body.to,
                body.company_name,
            )
            return test_run.id

    tasks = [run_one() for _ in range(body.num_emails)]
    run_ids = await asyncio.gather(*tasks)

    summary = create_test_summary_from_run_ids(
        db=db,
        run_ids=list(run_ids),
        concurrency_level=body.concurrency_level,
    )
    summary["run_ids"] = list(run_ids)
    return summary

class CreateTestFromRunsRequest(BaseModel):
    run_ids: List[int]
    concurrency_level: int = 1


@app.post("/tests/from-runs")
def create_test_from_runs(
    body: CreateTestFromRunsRequest,
    db: Session = Depends(get_db),
):
    return create_test_summary_from_run_ids(
        db=db,
        run_ids=body.run_ids,
        concurrency_level=body.concurrency_level,
    )