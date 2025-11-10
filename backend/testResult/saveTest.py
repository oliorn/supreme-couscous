from sqlalchemy import text
from datetime import datetime, timezone
import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from scraper.app.database import SessionLocal

def INSERT_TEST_DATA(settings: dict, results: dict) -> int:
    companies          = settings["companies"]
    num_emails         = settings["num_emails"]
    concurrency_level  = settings["concurrency_level"]

    started_at         = settings.get("started_at", datetime.now(timezone.utc))
    finished_at        = results.get("finished_at", datetime.now(timezone.utc))

    sql = text("""
        INSERT INTO tests (
            companies, num_emails, concurrency_level,
            started_at, finished_at,
            total_requests, ok_count, error_count, rate_limit_count, timeout_count, retry_count,
            sim_method, sim_avg, sim_p95
        )
        VALUES (
            :companies, :num_emails, :concurrency_level,
            :started_at, :finished_at,
            :total_requests, :ok_count, :error_count, :rate_limit_count, :timeout_count, :retry_count,
            :sim_method, :sim_avg, :sim_p95
        )
        RETURNING test_id;
    """)

    params = {
        "companies": companies,
        "num_emails": num_emails,
        "concurrency_level": concurrency_level,
        "started_at": started_at,
        "finished_at": finished_at,
        "total_requests": results.get("total_requests", 0),
        "ok_count": results.get("ok_count", 0),
        "error_count": results.get("error_count", 0),
        "rate_limit_count": results.get("rate_limit_count", 0),
        "timeout_count": results.get("timeout_count", 0),
        "retry_count": results.get("retry_count", 0),
        "sim_method": results.get("sim_method"),
        "sim_avg": results.get("sim_avg"),
        "sim_p95": results.get("sim_p95")
    }

    with SessionLocal() as session:
        result = session.execute(sql, params)
        test_id = result.scalar()
        session.commit()

    return test_id