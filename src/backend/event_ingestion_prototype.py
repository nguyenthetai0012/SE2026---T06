"""AI-assisted assignment prototype - initial baseline.

This first revision is intentionally retained in Git history for code review.
It is not production-ready: it demonstrates swallowed storage failures and
process-local deduplication so the refactor can be traced transparently.
The payload keys are illustrative and remain subject to the team contract.
"""

import sqlite3

SEEN_EVENT_IDS = set()


def ingest(db_path: str, event: dict) -> str:
    """Initial baseline: validation, persistence and deduplication are coupled."""
    try:
        event_id = event["event_id"]
        device_id = event["device_id"]
        measured_at = event["measured_at"]
        value = float(event["value"])

        if event_id in SEEN_EVENT_IDS:
            return "duplicate"

        with sqlite3.connect(db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS readings (
                    event_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    measured_at TEXT NOT NULL,
                    value REAL NOT NULL
                )
                """
            )
            connection.execute(
                "INSERT INTO readings(event_id, device_id, measured_at, value) "
                "VALUES (?, ?, ?, ?)",
                (event_id, device_id, measured_at, value),
            )

        SEEN_EVENT_IDS.add(event_id)
        return "accepted"
    except Exception as error:
        # Deliberate defect in the baseline: callers are told the event was
        # accepted even when validation or persistence failed.
        print(f"event processing failed: {error}")
        return "accepted"
