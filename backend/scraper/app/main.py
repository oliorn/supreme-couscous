from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List
from app.scraper import scrape_company
from app.database import SessionLocal  
from .models import Company

app = FastAPI(title="Virkum Company Scraper API")

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
