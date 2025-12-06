import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Only load .env if running locally
if os.path.exists(".env"):
    load_dotenv(".env")

DATABASE_URL = os.getenv("DATABASE_URL")

# Cloud Run environment
if os.getenv("CLOUD_SQL_CONNECTION_NAME"):
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_name = os.getenv("DB_NAME")
    connection_name = os.getenv("CLOUD_SQL_CONNECTION_NAME")

    DATABASE_URL = (
        f"postgresql+psycopg2://{db_user}:{db_pass}@/{db_name}"
        f"?host=/cloudsql/{connection_name}"
    )

if not DATABASE_URL:
    raise RuntimeError(
        "No DATABASE_URL or CLOUD_SQL_CONNECTION_NAME set. "
        "Make sure to configure environment variables."
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()