"""Seed chạy đồng thời với ghi reading: hai transaction trên PostgreSQL thật (review của Sương ở PR #42).

Quy tắc baseline: device đã có readings thì seed không được đổi building/chu kỳ/ngưỡng. Mọi đường ghi readings
phải khóa dòng device bằng SELECT ... FOR UPDATE trong cùng transaction; seed khóa cùng dòng trước khi đếm.

_worker_like_insert mô phỏng đúng thứ tự khóa của worker/ingest.py ở PR #41 (khóa device rồi chèn reading với
period_seconds của device). Khi #41 merge, thay helper này bằng worker.ingest.ingest.
Thứ tự hai transaction được điều khiển bằng pg_locks (chờ tới khi thấy bên kia đang đợi khóa), không dùng sleep cố định.
"""
from __future__ import annotations

import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor

import pytest
from loader import add_reading, load_fixture
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Device, Reading
from app.seed import SeedError, apply_seed, load_registry
from conftest import SEED_FILE

DEVICE = "A-01"
WAIT_S = 5          # thời gian tối đa chờ thấy transaction kia bị chặn
RESULT_S = 10       # thời gian tối đa chờ luồng phụ kết thúc


def _session(engine) -> Session:
    s = Session(engine)
    # SET LOCAL chỉ áp dụng cho transaction hiện tại của session: nếu một khóa không được nhả, lệnh chờ khóa
    # sẽ lỗi sau 10 s thay vì làm test treo vô hạn; connection trả về pool không mang theo thiết lập này.
    s.execute(text("SET LOCAL lock_timeout = '10s'"))
    return s


def _pid(s: Session) -> int:
    return s.execute(text("SELECT pg_backend_pid()")).scalar_one()


def _wait_blocked(engine, pid: int, future: Future) -> None:
    """Chờ tới khi backend `pid` đang đợi một khóa chưa được cấp."""
    deadline = time.monotonic() + WAIT_S
    with engine.connect() as c:
        while time.monotonic() < deadline:
            if future.done():
                pytest.fail(f"transaction kết thúc thay vì chờ khóa: {future.exception() or future.result()!r}")
            waiting = c.execute(text("SELECT EXISTS (SELECT 1 FROM pg_locks WHERE pid = :pid AND NOT granted)"),
                                {"pid": pid}).scalar_one()
            if waiting:
                return
            time.sleep(0.02)
    pytest.fail(f"không thấy backend {pid} chờ khóa trong {WAIT_S} s")


def _worker_like_insert(s: Session) -> int:
    """Như worker/ingest.py (#41): khóa device, chèn reading theo period hiện tại. Không commit."""
    dev = s.scalars(select(Device).where(Device.device_id == DEVICE).with_for_update()).one()
    add_reading(s, message_id=str(uuid.uuid4()), device_id=DEVICE, metric="power_kw",
                event_time="2026-10-27T00:00:00Z", received_at="2026-10-27T00:00:05Z", value=1)
    return dev.period_seconds


def _registry_with_period(period: int) -> dict:
    data = load_registry(SEED_FILE)
    next(d for d in data["devices"] if d["device_id"] == DEVICE)["period_seconds"] = period
    return data


def _device_period(engine) -> int:
    with engine.connect() as c:
        return c.execute(select(Device.period_seconds).where(Device.device_id == DEVICE)).scalar_one()


def _readings_with_other_period(engine) -> int:
    """Bất biến: không reading nào được diễn giải bằng chu kỳ khác với chu kỳ hiện tại của device."""
    with engine.connect() as c:
        return c.execute(text("SELECT count(*) FROM readings r JOIN devices d USING (device_id) "
                              "WHERE r.period_seconds <> d.period_seconds")).scalar_one()


def test_seed_waits_for_inflight_reading_then_refuses(engine, db):
    """Worker đi trước: đang giữ khóa và đã chèn reading chưa commit. Seed phải chờ, rồi thấy reading và từ chối."""
    assert _device_period(engine) == 60
    worker, seed = _session(engine), _session(engine)
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        _worker_like_insert(worker)
        pid = _pid(seed)
        future = pool.submit(apply_seed, seed, _registry_with_period(30))
        _wait_blocked(engine, pid, future)
        worker.commit()
        with pytest.raises(SeedError, match="period_seconds"):
            future.result(timeout=RESULT_S)
    finally:
        worker.rollback()
        worker.close()
        pool.shutdown(wait=True)
        seed.rollback()
        seed.close()
    assert _device_period(engine) == 60
    assert _readings_with_other_period(engine) == 0


def test_reading_after_seed_change_uses_new_period(engine, db, monkeypatch):
    """Seed đi trước: đã đổi chu kỳ (device chưa có reading) và giữ khóa. Worker phải chờ, rồi ghi theo chu kỳ mới."""
    seed, worker = _session(engine), _session(engine)
    # Giữ transaction của seed mở sau apply_seed để worker gặp khóa; commit thật ở dưới.
    monkeypatch.setattr(seed, "commit", seed.flush)
    pool = ThreadPoolExecutor(max_workers=1)

    def write_reading() -> int:
        period = _worker_like_insert(worker)
        worker.commit()
        return period

    try:
        diff = apply_seed(seed, _registry_with_period(30))
        assert diff["updated"] == [f"device:{DEVICE}(period_seconds)"]
        pid = _pid(worker)
        future = pool.submit(write_reading)
        _wait_blocked(engine, pid, future)
        Session.commit(seed)
        assert future.result(timeout=RESULT_S) == 30
    finally:
        seed.rollback()
        seed.close()
        pool.shutdown(wait=True)
        worker.rollback()
        worker.close()
    assert _device_period(engine) == 30
    with engine.connect() as c:
        assert c.execute(select(Reading.period_seconds).where(Reading.device_id == DEVICE)).scalars().all() == [30]
    assert _readings_with_other_period(engine) == 0


def test_seed_error_releases_device_lock(engine, db, fixture_data):
    """SeedError không được để lại khóa device: worker phải khóa được ngay, kể cả khi caller chưa rollback."""
    load_fixture(db, fixture_data)
    seed, other = _session(engine), _session(engine)
    try:
        with pytest.raises(SeedError, match="period_seconds"):
            apply_seed(seed, _registry_with_period(30))
        # Cố ý không gọi seed.rollback() ở đây.
        other.execute(select(Device).where(Device.device_id == DEVICE).with_for_update(nowait=True)).one()
    finally:
        other.rollback()
        other.close()
        seed.rollback()
        seed.close()
