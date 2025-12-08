from fastapi import FastAPI, Query, Depends, HTTPException, Body, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
import json
import random, time, requests
import os
import re
from openai import OpenAI
from app.scraper import scrape_company
from app.database import SessionLocal, engine  
from .models import Company, EmailSent, Base, EmailTestRun, ExpectedAnswer
from .email_service import get_email_service

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def generate_reply_with_openai(company_name: str, input_email: str):
    """
    Kallar á OpenAI chat/completions og skilar (subject, body, latency_ms).
    """
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")

    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
You are a representative of {company_name}.
Write a polite, professional reply to the following email:

{input_email}
"""

    llm_t0 = time.time()
    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.7,
    )
    llm_latency_ms = int((time.time() - llm_t0) * 1000)

    generated_body = completion.choices[0].message.content

    # Einföld subject-regla
    first_line = input_email.split("\n", 1)[0]
    if first_line.lower().startswith("subject:"):
        base_subject = first_line[len("Subject:"):].strip()
        generated_subject = f"Re: {base_subject}"
    else:
        generated_subject = f"Response from {company_name}"

    return generated_subject, generated_body, model_name, llm_latency_ms


def evaluate_with_openai_rubric(
    company_name: str,
    scenario: str,
    input_email: str,
    generated_body: str,
):
    """
    LLM-dómari sem GREFST EKKI ExpectedAnswer.
    Skilar (grade_float, latency_ms) þar sem grade er 1–10.
    """
    start = time.time()

    prompt = f"""
You are a strict reviewer grading an automatic customer support email reply.

COMPANY:
--------
{company_name}

SCENARIO:
---------
{scenario}

CUSTOMER EMAIL:
---------------
{input_email}

MODEL-GENERATED REPLY:
----------------------
{generated_body}

TASK:
Give a single numeric score from 1 to 10 indicating how good this reply is in terms of:
- correctness and factual accuracy
- helpfulness and clarity
- tone and professionalism
- whether it fully answers the customer’s request/complaint

Respond ONLY with the number, for example: 7.5
"""

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0.0,
    )

    latency_ms = int((time.time() - start) * 1000)
    text = resp.choices[0].message.content.strip()

    m = re.search(r"(\d+(\.\d+)?)", text)
    if not m:
        raise ValueError(f"Could not parse grade from: {text!r}")

    grade = float(m.group(1))
    grade = max(1.0, min(10.0, grade))   # clamp 1–10

    return grade, latency_ms

#  Create tables if they don't exist
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


SCENARIOS = [
    "Subject: Inquiry about your products\nDear team, I would like to know more about your skincare line...",
    "Subject: Complaint about delivery\nHello, my recent order arrived damaged...",
    "Subject: Question about ingredients\nHi, can you tell me if your products are suitable for sensitive skin?"
]

class SimulateRequest(BaseModel):
    company_name: Optional[str] = None
    to: EmailStr


def generate_reply_with_openai(company_name: str, input_email: str):
    """
    Hjálparfall sem kallar á OpenAI og skilar:
    (generated_subject, generated_body, model_name, llm_latency_ms)
    """
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)
    model_name = "gpt-4.1-mini"

    prompt = f"""
You are a representative of the company "{company_name}".

You received the following email from a customer:

{input_email}

1) First, infer an appropriate email subject line.
2) Then, write a professional, friendly email reply.

Return your result in JSON with the fields:
- subject
- body
"""

    t0 = time.time()
    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=600,
    )
    llm_latency_ms = int((time.time() - t0) * 1000)

    content = resp.choices[0].message.content
    import json
    try:
        parsed = json.loads(content)
    except Exception:
        raise HTTPException(status_code=500, detail="LLM returned invalid JSON")

    generated_subject = parsed.get("subject", "").strip()
    generated_body = parsed.get("body", "").strip()

    if not generated_body:
        raise HTTPException(status_code=500, detail="LLM did not return a body")

    return generated_subject, generated_body, model_name, llm_latency_ms


@app.post("/simulate-email")
def simulate_email(
    body: SimulateRequest,
    db: Session = Depends(get_db)
):
    """
    Býr til mock email, kallar á OpenAI til að búa til svar,
    sendir email og vistar allt í EmailTestRuns (með reply_grade ef til er ExpectedAnswer).
    """

    # 1) Velja company_name (beint eða random úr DB)
    if body.company_name:
        company_name = body.company_name
    else:
        result = db.execute(
            text('SELECT "CompanyName" FROM "Companies" ORDER BY RANDOM() LIMIT 1')
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="No companies available in database")
        company_name = row[0]

    # 2) Velja random scenario sem input_email
    input_email = random.choice(SCENARIOS)
    # Scenario = fyrsti línan (t.d. "Subject: Complaint about delivery")
    scenario = input_email.split("\n", 1)[0].strip()

    # 3) Kalla á OpenAI til að fá svarið
    try:
        generated_subject, generated_body, model_name, llm_latency_ms = generate_reply_with_openai(
            company_name=company_name,
            input_email=input_email,
        )
    except HTTPException as e:
        # Vista failed run (ef þú vilt) og kasta svo áfram
        test_run = EmailTestRun(
            company_name=company_name,
            scenario=scenario,
            input_email=input_email,
            generated_body=None,
            generated_subject=None,
            model_name="gpt-4.1-mini",
            latency_ms=None,
            sent_ok=False,
        )
        db.add(test_run)
        db.commit()
        db.refresh(test_run)
        raise

    # 4) EKKI lengur senda email í gegnum /send-email – bara simulate
    sent_ok = False
    send_message = "Simulation only – email was NOT actually sent."
    send_latency_ms = 0

    total_latency_ms = llm_latency_ms + send_latency_ms


    # --- 5) Vista í EmailTestRuns (núna með RÉTTUM dálkum) ---
    test_run = EmailTestRun(
        company_name=company_name,
        scenario=scenario,
        input_email=input_email,
        generated_subject=generated_subject,
        generated_body=generated_body,
        model_name="gpt-4.1-mini",
        latency_ms=total_latency_ms,
        sent_ok=sent_ok,
    )

    # 5.5)  AUTO-GRADING: LLM-dómari, engin ExpectedAnswer lengur
    try:
        grade, eval_latency_ms = evaluate_with_openai_rubric(
            company_name=company_name,
            scenario=scenario,
            input_email=input_email,
            generated_body=generated_body,
        )
        test_run.reply_grade = grade
    except Exception as e:
        # ef dómari bregst, viljum ekki drepa allt endpointið
        print(f"LLM grading failed: {e}")
        # test_run.reply_grade verður þá bara None


    # 6) Vista test_run
    db.add(test_run)
    db.commit()
    db.refresh(test_run)

    # 7) Skila niðurstöðu til UI
    return {
        "status": "ok",
        "company_used": company_name,
        "latency_ms": total_latency_ms,
        "llm_latency_ms": llm_latency_ms,
        "sent_ok": sent_ok,
        "test_run_id": test_run.id,
        "preview": {
            "scenario": scenario,
            "input_email": input_email,
            "generated_subject": generated_subject,
            "generated_body": generated_body,
            "send_message": send_message,
            "reply_grade": float(test_run.reply_grade) if test_run.reply_grade is not None else None,
        },
    }

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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



from typing import List

class CreateTestFromRunsRequest(BaseModel):
    run_ids: List[int]
    concurrency_level: int = 1


@app.post("/tests/from-runs")
def create_test_from_runs(
    body: CreateTestFromRunsRequest,
    db: Session = Depends(get_db),
):
    """
    Take a list of EmailTestRun IDs, compute summary and insert one row into tests.
    Used by the 'Run simulated test' button.
    """
    if not body.run_ids:
        raise HTTPException(status_code=400, detail="run_ids cannot be empty")

    # 1) Fetch all runs in this batch
    runs = (
        db.query(EmailTestRun)
        .filter(EmailTestRun.id.in_(body.run_ids))
        .all()
    )
    if not runs:
        raise HTTPException(status_code=404, detail="No EmailTestRuns found for given IDs")

    # 2) Compute stats
    companies = sorted({r.company_name for r in runs if r.company_name})
    num_emails = len(runs)
    total_requests = num_emails  # or adjust if you ever do retries

    grades = [float(r.reply_grade) for r in runs if r.reply_grade is not None]
    avg_reply_grade = sum(grades) / len(grades) if grades else None

    # 3) Started/finished timestamps (you might have created_at/sent_at)
    started_at = min(r.created_at for r in runs) if hasattr(runs[0], "created_at") else datetime.utcnow()
    finished_at = max(r.created_at for r in runs) if hasattr(runs[0], "created_at") else datetime.utcnow()

    # If your tests.companies column is JSON/JSONB:
    companies_json = json.dumps(companies)

    # 4) Insert into tests table and return test_id
    insert_sql = text("""
        INSERT INTO tests (
            companies,
            num_emails,
            concurrency_level,
            started_at,
            finished_at,
            total_requests,
            avg_reply_grade
        )
        VALUES (
            :companies,
            :num_emails,
            :concurrency_level,
            :started_at,
            :finished_at,
            :total_requests,
            :avg_reply_grade
        )
        RETURNING test_id
    """)

    result = db.execute(
        insert_sql,
        {
            "companies": companies_json,
            "num_emails": num_emails,
            "concurrency_level": body.concurrency_level,
            "started_at": started_at,
            "finished_at": finished_at,
            "total_requests": total_requests,
            "avg_reply_grade": avg_reply_grade,
        },
    )
    db.commit()

    new_test_id = result.fetchone()[0]

    return {
        "status": "ok",
        "test_id": new_test_id,
        "companies": companies,
        "num_emails": num_emails,
        "concurrency_level": body.concurrency_level,
        "total_requests": total_requests,
        "avg_reply_grade": avg_reply_grade,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
    }
