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

# Read local DATABASE_URL if running locally
DATABASE_URL = os.getenv("DATABASE_URL")

# Fyrir Cloud run
if os.getenv("CLOUD_SQL_CONNECTION_NAME"):
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_name = os.getenv("DB_NAME")
    connection_name = os.getenv("CLOUD_SQL_CONNECTION_NAME")

    # Cloud SQL socket-based URL (Postgres)
    DATABASE_URL = (
        f"postgresql+psycopg2://{db_user}:{db_pass}@/{db_name}"
        f"?host=/cloudsql/{connection_name}"
    )

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set and CLOUD_SQL_CONNECTION_NAME not provided")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
