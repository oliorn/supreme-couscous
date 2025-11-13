from datetime import datetime, timezone
from saveTest import INSERT_TEST_DATA

def main():
    settings = {
        "companies": ["Company A", "Company B"],
        "num_emails": 20,
        "concurrency_level": 5
    }

    # Results collected after the test finishes
    results = {
        "finished_at": datetime.now(timezone.utc),
        "total_requests": 20,
        "ok_count": 18,
        "error_count": 2,
        "rate_limit_count": 0,
        "timeout_count": 1,
        "retry_count": 1,
        "sim_method": "cosine",
        "sim_avg": 0.82,
        "sim_p95": 0.91
    }

    # Save to DB
    test_id = INSERT_TEST_DATA(settings, results)
    print(f"Test saved to database with test_id = {test_id}")


if __name__ == "__main__":
    main()
