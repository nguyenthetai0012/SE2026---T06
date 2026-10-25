"""AI-assisted assignment prototype for event delivery and recovery.

Status: assignment prototype only; not approved as the team stack or contract.
It uses Python's standard library and SQLite so the behavior is reviewable
without choosing a web framework, MQTT client, or external dependency.

The payload keys below (event_id, device_id, building_id, measured_at,
metric, value, unit) are illustrative until the team approves the MQTT schema.
"""

from __future__ import annotations

import math
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping


class EventValidationError(ValueError):
    """The event does not satisfy the prototype's illustrative payload rules."""


class EventStoreUnavailable(RuntimeError):
    """The local store could not durably accept an event after bounded retries."""


@dataclass(frozen=True)
class ValidatedEvent:
    event_id: str
    device_id: str
    building_id: str
    measured_at: str
    metric: str
    value: float
    unit: str


@dataclass(frozen=True)
class IngestResult:
    event_id: str
    status: str  # "accepted" or "duplicate"


def _format_utc(value: datetime) -> str:
    return (
        value.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _required_text(event: Mapping[str, Any], key: str) -> str:
    value = event.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EventValidationError(f"{key} must be a non-empty string")
    return value.strip()


def _utc_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise EventValidationError("measured_at must be an ISO-8601 timestamp") from error

    if parsed.tzinfo is None:
        raise EventValidationError("measured_at must include a UTC offset")

    return _format_utc(parsed)


def validate_event(payload: Mapping[str, Any]) -> ValidatedEvent:
    """Validate and normalize the illustrative event contract."""
    event_id = _required_text(payload, "event_id")
    device_id = _required_text(payload, "device_id")
    building_id = _required_text(payload, "building_id")
    metric = _required_text(payload, "metric")
    unit = _required_text(payload, "unit")
    measured_at = _utc_timestamp(_required_text(payload, "measured_at"))

    raw_value = payload.get("value")
    if isinstance(raw_value, bool):
        raise EventValidationError("value must be a finite number")
    try:
        numeric_value = float(raw_value)
    except (TypeError, ValueError) as error:
        raise EventValidationError("value must be a finite number") from error
    if not math.isfinite(numeric_value):
        raise EventValidationError("value must be a finite number")

    return ValidatedEvent(
        event_id=event_id,
        device_id=device_id,
        building_id=building_id,
        measured_at=measured_at,
        metric=metric,
        value=numeric_value,
        unit=unit,
    )


class SQLiteEventRepository:
    """Owns durable readings and enforces event-level idempotency."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=0.1)
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._transaction() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS readings (
                    event_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    building_id TEXT NOT NULL,
                    measured_at TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    received_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_readings_measured_at "
                "ON readings(measured_at)"
            )

    def save_once(self, event: ValidatedEvent, received_at: str) -> bool:
        """Return True for a new row, False when this event ID already exists."""
        self.initialize()
        with self._transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO readings(
                    event_id, device_id, building_id, measured_at,
                    metric, value, unit, received_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO NOTHING
                """,
                (
                    event.event_id,
                    event.device_id,
                    event.building_id,
                    event.measured_at,
                    event.metric,
                    event.value,
                    event.unit,
                    received_at,
                ),
            )
            inserted = cursor.rowcount == 1
        return inserted

    def purge_before(self, cutoff_utc: str) -> int:
        """Delete readings older than the supplied UTC cutoff."""
        with self._transaction() as connection:
            cursor = connection.execute(
                "DELETE FROM readings WHERE measured_at < ?",
                (cutoff_utc,),
            )
            deleted = cursor.rowcount
        return deleted


class EventIngestionService:
    """Coordinates validation, bounded retry, idempotent save, and retention."""

    def __init__(
        self,
        repository: SQLiteEventRepository,
        *,
        max_attempts: int = 3,
        initial_backoff_seconds: float = 0.05,
        retention_days: int = 28,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if initial_backoff_seconds < 0:
            raise ValueError("initial_backoff_seconds cannot be negative")
        if retention_days < 1:
            raise ValueError("retention_days must be at least 1")

        self.repository = repository
        self.max_attempts = max_attempts
        self.initial_backoff_seconds = initial_backoff_seconds
        self.retention_days = retention_days

    def ingest(
        self,
        payload: Mapping[str, Any],
        *,
        received_at: datetime | None = None,
    ) -> IngestResult:
        event = validate_event(payload)
        received = received_at or datetime.now(timezone.utc)
        received_text = _format_utc(received)

        for attempt in range(self.max_attempts):
            try:
                inserted = self.repository.save_once(event, received_text)
                return IngestResult(
                    event_id=event.event_id,
                    status="accepted" if inserted else "duplicate",
                )
            except sqlite3.OperationalError as error:
                # Only SQLite lock contention is retried. Other storage errors
                # surface immediately so callers cannot acknowledge a lost event.
                message = str(error).lower()
                if "locked" not in message and "busy" not in message:
                    raise EventStoreUnavailable(
                        f"storage failed for event {event.event_id}"
                    ) from error
                if attempt + 1 == self.max_attempts:
                    raise EventStoreUnavailable(
                        f"storage stayed busy for event {event.event_id}"
                    ) from error
                delay = self.initial_backoff_seconds * (2**attempt)
                if delay:
                    time.sleep(delay)

        raise AssertionError("unreachable retry state")

    def purge_expired(self, *, now: datetime | None = None) -> int:
        current = now or datetime.now(timezone.utc)
        cutoff = current.astimezone(timezone.utc) - timedelta(days=self.retention_days)
        return self.repository.purge_before(_format_utc(cutoff))


def example_event() -> dict[str, Any]:
    """Return a deterministic sample payload for manual exploration."""
    return {
        "event_id": "sample-evt-001",
        "device_id": "meter-01",
        "building_id": "building-a",
        "measured_at": "2026-10-25T03:00:00Z",
        "metric": "energy",
        "value": 12.5,
        "unit": "kWh",
    }
