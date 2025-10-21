from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from app.scraper import scrape_company

app = FastAPI(title="Virkum Company Scraper API")


# Allow local and GCP access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "✅ Scraper service is running."}

@app.get("/scrape")
def scrape(url: str = Query(..., description="Public website URL")):
    """Scrape a company's public website and return structured info."""
    data = scrape_company(url)
    return data
