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