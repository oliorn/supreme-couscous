import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Path to this file: backend/scraper/app/database.py
BASE_DIR = Path(__file__).resolve()

# Go up: app -> scraper -> backend -> project root
PROJECT_ROOT = BASE_DIR.parents[3]

# Load .env from project root (SUPREME-COUSCOUS/.env)
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
