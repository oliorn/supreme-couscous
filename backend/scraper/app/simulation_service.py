# app/simulation_service.py
import json, random
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import text

from .database import SessionLocal
from .models import EmailTestRun
from .llm_service import generate_reply_with_openai, evaluate_with_openai_rubric

SCENARIOS = [
    "Subject: Inquiry about your products\nDear team, I would like to know more about your skincare line...",
    "Subject: Complaint about delivery\nHello, my recent order arrived damaged...",
    "Subject: Question about ingredients\nHi, can you tell me if your products are suitable for sensitive skin?"
]


def run_single_simulation(
    to_email: str,
    company_name: Optional[str] = None,
) -> Tuple[EmailTestRun, int, int]:
    db = SessionLocal()
    try:
        # 1) choose company
        if company_name:
            chosen_company = company_name
        else:
            result = db.execute(
                text('SELECT "CompanyName" FROM "Companies" ORDER BY RANDOM() LIMIT 1')
            )
            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=400, detail="No companies available in database")
            chosen_company = row[0]

        # 2) scenario
        input_email = random.choice(SCENARIOS)
        scenario = input_email.split("\n", 1)[0].strip()

        # 3) LLM reply
        try:
            subj, body, model_name, llm_latency_ms = generate_reply_with_openai(
                company_name=chosen_company,
                input_email=input_email,
            )
        except HTTPException:
            test_run = EmailTestRun(
                company_name=chosen_company,
                scenario=scenario,
                input_email=input_email,
                generated_subject=None,
                generated_body=None,
                model_name="gpt-4.1-mini",
                latency_ms=None,
                sent_ok=False,
            )
            db.add(test_run)
            db.commit()
            db.refresh(test_run)
            raise

        total_latency_ms = llm_latency_ms

        test_run = EmailTestRun(
            company_name=chosen_company,
            scenario=scenario,
            input_email=input_email,
            generated_subject=subj,
            generated_body=body,
            model_name="gpt-4.1-mini",
            latency_ms=total_latency_ms,
            sent_ok=False,
        )

        # grading
        try:
            grade, _ = evaluate_with_openai_rubric(
                company_name=chosen_company,
                scenario=scenario,
                input_email=input_email,
                generated_body=body,
            )
            test_run.reply_grade = grade
        except Exception as e:
            print(f"LLM grading failed: {e}")

        db.add(test_run)
        db.commit()
        db.refresh(test_run)

        return test_run, total_latency_ms, llm_latency_ms

    finally:
        db.close()


def create_test_summary_from_run_ids(db, run_ids: List[int], concurrency_level: int):
    if not run_ids:
        raise HTTPException(status_code=400, detail="run_ids cannot be empty")

    runs = (
        db.query(EmailTestRun)
        .filter(EmailTestRun.id.in_(run_ids))
        .all()
    )
    if not runs:
        raise HTTPException(status_code=404, detail="No EmailTestRuns found for given IDs")

    companies = sorted({r.company_name for r in runs if r.company_name})
    num_emails = len(runs)
    total_requests = num_emails

    grades = [float(r.reply_grade) for r in runs if r.reply_grade is not None]
    avg_reply_grade = sum(grades) / len(grades) if grades else None

    started_at = min(getattr(r, "created_at", datetime.utcnow()) for r in runs)
    finished_at = max(getattr(r, "created_at", datetime.utcnow()) for r in runs)

    companies_json = json.dumps(companies)

    insert_sql = text("""
        INSERT INTO tests (
            companies,
            num_emails,
            concurrency_level,
            started_at,
            finished_at,
            total_requests,
            avg_reply_grade
        )
        VALUES (
            :companies,
            :num_emails,
            :concurrency_level,
            :started_at,
            :finished_at,
            :total_requests,
            :avg_reply_grade
        )
        RETURNING test_id
    """)

    result = db.execute(
        insert_sql,
        {
            "companies": companies_json,
            "num_emails": num_emails,
            "concurrency_level": concurrency_level,
            "started_at": started_at,
            "finished_at": finished_at,
            "total_requests": total_requests,
            "avg_reply_grade": avg_reply_grade,
        },
    )
    db.commit()
    new_test_id = result.fetchone()[0]

    return {
        "status": "ok",
        "test_id": new_test_id,
        "companies": companies,
        "num_emails": num_emails,
        "concurrency_level": concurrency_level,
        "total_requests": total_requests,
        "avg_reply_grade": avg_reply_grade,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
    }