"""VT-022: hành vi mong đợi khi gửi thông báo cho alert.

Các test dùng fixture PostgreSQL riêng của repo. Module được gọi dưới đây
sẽ được triển khai sau khi ghi nhận kết quả test thất bại đúng lý do.
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Alert, Reading


def payload():
    return {
        "message_id": str(uuid4()), "device_id": "A-01",
        "event_time": datetime(2026, 10, 27, 0, 1, tzinfo=timezone.utc),
        "value_kw": Decimal("12"),
    }


def test_notification_failure_does_not_undo_committed_reading_and_alert(engine, db):
    from app.vt022_notification import process_reading

    event = payload()

    def failing_sender(_alert):
        raise OSError("simulated notification failure")

    result = process_reading(engine, event, failing_sender)
    assert result.notification_status == "failed"
    with Session(engine) as fresh_session:
        reading = fresh_session.get(Reading, event["message_id"])
        alert = fresh_session.query(Alert).filter_by(message_id=event["message_id"]).one()
        assert reading is not None
        assert reading.value == Decimal("12")
        assert alert.value_kw == Decimal("12")
        assert alert.threshold_kw == Decimal("10")


def test_successful_alert_sends_notification_after_commit(engine, db):
    from app.vt022_notification import process_reading

    event = payload()
    observed = []

    def sender(alert):
        with Session(engine) as fresh_session:
            observed.append(fresh_session.get(Alert, alert.alert_id) is not None)

    result = process_reading(engine, event, sender)
    assert observed == [True]
    assert result.notification_status == "sent"
