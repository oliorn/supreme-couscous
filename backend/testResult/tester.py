from datetime import datetime, timezone
from saveTest import INSERT_TEST_DATA

def main():
    settings = {
        "companies": ["Company A", "Company B"],
        "num_emails": 20,
        "concurrency_level": 5,
    }

    avg_reply_grade = 0.87

    results = {
        "finished_at": datetime.now(timezone.utc),
        "total_requests": 20,
        "avg_reply_grade": avg_reply_grade,
    }

    # Save to DB
    test_id = INSERT_TEST_DATA(settings, results)
    print(f"Test saved to database with test_id = {test_id}")


if __name__ == "__main__":
    main()
