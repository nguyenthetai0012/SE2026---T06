"""Contract tests chạy trên PostgreSQL thật qua Alembic (không dùng create_all để ràng buộc là thật).

Cần biến môi trường TEST_DATABASE_URL trỏ tới một database dành riêng cho test (tên chứa 'test').
Fixture sẽ DROP SCHEMA public của database đó. Thiếu biến -> dừng với thông báo rõ, không bỏ qua im lặng.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import Settings
from app.main import create_app
from app.seed import apply_seed, load_registry

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "src" / "backend"
FIXTURE = ROOT / "docs" / "testing" / "fixtures" / "mvp-normal.json"
SEED_FILE = BACKEND / "seed" / "registry.json"


def utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.exit("Thiếu TEST_DATABASE_URL (ví dụ postgresql+psycopg://user@localhost:5432/energy_test). "
                    "Database này sẽ bị DROP SCHEMA public.", returncode=2)
    name = make_url(url).database or ""
    if "test" not in name:
        pytest.exit(f"Từ chối chạy: tên database '{name}' không chứa 'test'.", returncode=2)
    return url


@pytest.fixture(scope="session")
def engine(database_url):
    eng = create_engine(database_url, connect_args={"options": "-c timezone=UTC"})
    with eng.begin() as c:
        c.execute(text("DROP SCHEMA public CASCADE"))
        c.execute(text("CREATE SCHEMA public"))
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        command.upgrade(cfg, "head")
    finally:
        if old is None:
            os.environ.pop("DATABASE_URL")
        else:
            os.environ["DATABASE_URL"] = old
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    with engine.begin() as c:
        c.execute(text("TRUNCATE alerts, readings, devices, buildings RESTART IDENTITY CASCADE"))
    with Session(engine) as session:
        apply_seed(session, load_registry(SEED_FILE))
        yield session


@pytest.fixture()
def fixture_data() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class Clock:
    def __init__(self, value: datetime):
        self.value = value

    def __call__(self) -> datetime:
        return self.value


@pytest.fixture()
def clock(fixture_data) -> Clock:
    return Clock(utc(fixture_data["clock"]))


@pytest.fixture()
def client(database_url, db, clock):
    app = create_app(Settings(database_url=database_url), clock=clock)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.state.engine.dispose()
