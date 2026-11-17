"""Cấu hình, lỗi hạ tầng, request id, OpenAPI trùng contract."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import ConfigError, Settings
from app.main import create_app
from conftest import ROOT


def test_settings_require_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ConfigError, match="DATABASE_URL"):
        Settings.from_env()
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u@h/d")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(ConfigError, match="wildcard"):
        Settings.from_env()
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("DB_STATEMENT_TIMEOUT_MS", "0")
    with pytest.raises(ConfigError):
        Settings.from_env()


def test_db_down_is_503_not_empty(database_url):
    app = create_app(Settings(database_url="postgresql+psycopg://nobody@127.0.0.1:1/none"))
    with TestClient(app, raise_server_exceptions=False) as c:
        for path in ("/api/v1/health/ready", "/api/v1/devices"):
            r = c.get(path)
            assert r.status_code == 503, path
            err = r.json()["error"]
            assert err["code"] == "DEPENDENCY_UNAVAILABLE" and err["request_id"]
            assert "nobody" not in r.text and "127.0.0.1" not in r.text       # không lộ chi tiết kết nối
    app.state.engine.dispose()


def test_statement_timeout_is_applied_to_every_connection(database_url, db):
    from sqlalchemy import text
    app = create_app(Settings(database_url=database_url, statement_timeout_ms=1234))
    with app.state.engine.connect() as conn:
        assert conn.execute(text("SHOW statement_timeout")).scalar() == "1234ms"
        assert conn.execute(text("SHOW timezone")).scalar() == "UTC"
    app.state.engine.dispose()


def test_request_id_generated_and_unsafe_value_replaced(client):
    r = client.get("/api/v1/devices?bad=1")
    assert re.fullmatch(r"[0-9a-f]{32}", r.json()["error"]["request_id"]) and r.headers["X-Request-ID"] == r.json()["error"]["request_id"]
    r = client.get("/api/v1/devices?bad=1", headers={"X-Request-ID": "bad id\r\nX: y"})
    assert re.fullmatch(r"[0-9a-f]{32}", r.json()["error"]["request_id"])


def test_cors_allowlist_only(database_url):
    app = create_app(Settings(database_url=database_url, cors_origins=("http://localhost:5173",)))
    with TestClient(app) as c:
        ok = c.get("/api/v1/health/ready", headers={"Origin": "http://localhost:5173"})
        bad = c.get("/api/v1/health/ready", headers={"Origin": "http://evil.example"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers
    app.state.engine.dispose()


def test_only_get_methods_exposed(client):
    for method in ("post", "put", "delete", "patch"):
        assert getattr(client, method)("/api/v1/devices").status_code == 405


def test_openapi_matches_contract_and_checked_in_file(client):
    spec = client.get("/openapi.json").json()
    paths = {p: sorted(m) for p, m in spec["paths"].items()}
    assert paths == {
        "/api/v1/buildings/summary": ["get"], "/api/v1/devices": ["get"],
        "/api/v1/devices/{device_id}/readings": ["get"], "/api/v1/alerts": ["get"], "/api/v1/health/ready": ["get"],
    }
    schemas = spec["components"]["schemas"]
    fields = {k: set(schemas[k]["properties"]) for k in ("BuildingSummary", "Device", "Reading", "Alert")}
    assert fields == {
        "BuildingSummary": {"building_id", "name", "energy_kwh", "unit", "start", "end", "included_interval_count",
                            "coverage", "coverage_ratio", "data_stale"},
        "Device": {"device_id", "building_id", "name", "enabled", "status", "last_seen", "latest_event_time", "data_stale", "period_seconds"},
        "Reading": {"message_id", "device_id", "building_id", "metric", "event_time", "received_at", "interval_start",
                    "value", "unit", "is_late", "is_out_of_order"},
        "Alert": {"alert_id", "message_id", "device_id", "building_id", "event_time", "detected_at", "metric", "value",
                  "threshold", "unit", "description"},
    }
    # Mọi field bắt buộc kể cả nullable (contract: bắt buộc trừ khi ghi nullable -> nullable vẫn có mặt).
    for k in fields:
        assert set(schemas[k]["required"]) == fields[k], k
    checked_in = ROOT / "docs" / "contracts" / "mvp-openapi.json"
    assert json.loads(checked_in.read_text(encoding="utf-8")) == spec, \
        "mvp-openapi.json lệch với app; chạy: python tools/scripts/export_openapi.py"
