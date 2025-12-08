from sqlalchemy import text
from datetime import datetime, timezone
import sys
import os
import json
from scraper.app.database import SessionLocal
from app.database import SessionLocal

#sys.path.append(os.path.join(os.path.dirname(__file__), '..'))



def INSERT_TEST_DATA(settings: dict, results: dict) -> int:
    companies         = settings["companies"]
    num_emails        = settings["num_emails"]
    concurrency_level = settings["concurrency_level"]

    started_at  = settings.get("started_at", datetime.now(timezone.utc))
    finished_at = results.get("finished_at", datetime.now(timezone.utc))

    sql = text("""
        INSERT INTO tests (
            companies, num_emails, concurrency_level,
            started_at, finished_at,
            total_requests, avg_reply_grade
        )
        VALUES (
            :companies, :num_emails, :concurrency_level,
            :started_at, :finished_at,
            :total_requests, :avg_reply_grade
        )
        RETURNING test_id;
    """)

    params = {
        "companies": json.dumps(companies),
        "num_emails": num_emails,
        "concurrency_level": concurrency_level,
        "started_at": started_at,
        "finished_at": finished_at,
        "total_requests": results.get("total_requests", 0),
        "avg_reply_grade": results.get("avg_reply_grade"),
    }

    with SessionLocal() as session:
        result = session.execute(sql, params)
        test_id = result.scalar()
        session.commit()

    return test_id
