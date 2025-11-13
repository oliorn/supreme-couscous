from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.scraper import scrape_company
from app.database import SessionLocal  

app = FastAPI(title="Virkum Company Scraper API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
