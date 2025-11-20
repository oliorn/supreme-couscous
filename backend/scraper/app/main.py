from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List
from app.scraper import scrape_company
from app.database import SessionLocal  
from .models import Company
import os, requests
from pathlib import Path
from dotenv import load_dotenv

app = FastAPI(title="Virkum Company Scraper API")

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "false").lower() == "true"

# --- CORS so React (localhost:3000) can talk to FastAPI ---
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000", ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CompanyOut(BaseModel):
    CompanyName: str
    CompanyDescription: str | None = None
    CompanyInfo: str | None = None

    class Config:
        orm_mode = True

# DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class EmailRequest(BaseModel):
    company_name: str
    topic: str | None = None     # t.d. Virkum „Topic Template“ síðar
    tone: str | None = "friendly"
    language: str | None = "en"

class EmailResponse(BaseModel):
    email: str


@app.post("/llm/generate-email", response_model=EmailResponse)
def generate_email(req: EmailRequest):
    # 1) Mock-mode til að spara pening á meðan verið er að prófa
    if USE_MOCK_LLM:
        fake = (
            f"Subject: Test email for {req.company_name}\n\n"
            f"Hi,\n\n"
            f"This is a MOCK email about '{req.topic or 'general information'}' "
            f"for {req.company_name}. No real LLM call was made.\n\n"
            f"Best regards,\nTest System"
        )
        return EmailResponse(email=fake)

    # 2) Öryggis-check
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    # 3) Smíða prompt (síðar getum við fléttað inn Virkum template upplýsingum)
    prompt = (
        f"Generate a professional but slightly informal business email "
        f"about '{req.topic or 'a generic inquiry'}' for the company {req.company_name}. "
        f"Language: {req.language}. 2-3 paragraphs."
    )

    # 4) Hringja í OpenAI Chat Completions API (eins og í leiðbeiningunum)
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4.1-mini",   # ódýrt módel
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.7,
            },
            timeout=20,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling OpenAI: {e}")

    if resp.status_code != 200:
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        raise HTTPException(status_code=resp.status_code, detail=str(err))

    data = resp.json()
    email_text = data["choices"][0]["message"]["content"]

    return EmailResponse(email=email_text)

@app.get("/companies", response_model=List[CompanyOut])
def list_companies(db: Session = Depends(get_db)):
    # Use raw SQL, like in /scrape, matching your table/column names exactly
    result = db.execute(
        text(
            """
            SELECT "CompanyName", "CompanyDescription", "CompanyInfo"
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
    # sækja gögn
    data = scrape_company(url)
    if "error" in data:
        raise HTTPException(status_code=400, detail=data["error"])

    # mappar í dálkana í postgres töflunni
    name = data.get("company_name") or ""
    descr = data.get("company_description") or ""
    info = data.get("company_information") or ""

    
    saved = False
    error = None
    try:
        db.execute(
            text(
                """
                INSERT INTO "Companies" ("CompanyName", "CompanyDescription", "CompanyInfo")
                VALUES (:name, :descr, :info)
                """
            ),
            {"name": name, "descr": descr, "info": info},
        )
        db.commit()
        saved = True
    except Exception as e:
        error = str(e)

    return {
        "saved": saved,
        "db_error": error,
        "scraped": data,
    }
