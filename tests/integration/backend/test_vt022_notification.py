"""VT-022: hành vi mong đợi khi gửi thông báo cho alert.

Các test dùng fixture PostgreSQL riêng của repo. Module được gọi dưới đây
sẽ được triển khai sau khi ghi nhận kết quả test thất bại đúng lý do.
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
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


@pytest.mark.parametrize("value,expected", [(Decimal("0"), "not_required"),
    (Decimal("9.999"), "not_required"), (Decimal("10"), "not_required"),
    (Decimal("10.001"), "sent")])
def test_threshold_partitions(engine, db, value, expected):
    from app.vt022_notification import process_reading
    event = payload()
    event["value_kw"] = value
    sent = []
    result = process_reading(engine, event, lambda alert: sent.append(alert.alert_id))
    assert result.notification_status == expected
    assert len(sent) == (1 if expected == "sent" else 0)
    with Session(engine) as session:
        assert session.get(Reading, event["message_id"]) is not None
        assert session.query(Alert).filter_by(message_id=event["message_id"]).count() == len(sent)


@pytest.mark.parametrize("invalid", [-1, "12", True, Decimal("NaN"), Decimal("Infinity")])
def test_invalid_value_rejected_before_write(engine, db, invalid):
    from app.vt022_notification import process_reading
    event = payload()
    event["value_kw"] = invalid
    sent = []
    with pytest.raises(ValueError):
        process_reading(engine, event, sent.append)
    with Session(engine) as session:
        assert session.get(Reading, event["message_id"]) is None
    assert sent == []


def test_oversized_input_rejected_before_write(engine, db):
    from app.vt022_notification import process_reading
    event = payload()
    event["device_id"] = "A" * 4097
    sent = []
    with pytest.raises(ValueError, match="size"):
        process_reading(engine, event, sent.append)
    assert sent == []
    with Session(engine) as session:
        assert session.get(Reading, event["message_id"]) is None


def test_failed_database_insert_does_not_send_again(engine, db):
    from app.vt022_notification import process_reading
    event = payload()
    process_reading(engine, event, lambda alert: None)
    sent = []
    with pytest.raises(IntegrityError):
        process_reading(engine, event, sent.append)
    assert sent == []
    with Session(engine) as session:
        assert session.query(Alert).filter_by(message_id=event["message_id"]).count() == 1


def test_alert_api_maps_value_and_threshold(engine, client):
    from app.vt022_notification import process_reading
    event = payload()
    process_reading(engine, event, lambda alert: None)
    response = client.get("/api/v1/alerts", params={"device_id": "A-01"})
    assert response.status_code == 200
    item = next(item for item in response.json()["data"] if item["message_id"] == event["message_id"])
    assert item["value"] == 12
    assert item["threshold"] == 10
