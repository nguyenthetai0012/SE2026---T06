"""MQTT consumer (Paho 2, MQTT 3.1.1, QoS 1): subscribe campus/v1/+/+/readings và gọi ingest().

    cd src/backend && DATABASE_URL=... MQTT_HOST=... python -m worker.consumer

Quyết định MVP (chờ nhóm xác nhận): ACK thủ công SAU khi commit. Lỗi DB -> không ACK, ngắt rồi nối lại sau 5 giây để broker
gửi lại (session bền, client_id cố định); bản gửi lại được chống trùng bằng idempotency.
Bản tin bị từ chối (invalid/conflict) vẫn được ACK và chỉ đếm theo mã; không publish lỗi vào topic readings.
Chưa có HTTP health endpoint; trạng thái hiện ghi qua log và bộ đếm `Stats`.
"""
from __future__ import annotations

import logging
import os
import signal
import sys
import threading
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import ConfigError, Settings
from app.db import make_engine

from .ingest import ingest

log = logging.getLogger("worker")
SUBSCRIBE_TOPIC = "campus/v1/+/+/readings"
RETRY_DELAY_SECONDS = 5


class Stats:
    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.db_failures = 0
        self.connected = False

    def note(self, status: str, code: str | None) -> None:
        self.counts[f"{status}:{code}" if code else status] += 1


def mqtt_settings() -> dict:
    host = os.environ.get("MQTT_HOST", "").strip()
    if not host:
        raise ConfigError("Thiếu biến môi trường MQTT_HOST.")
    try:
        port = int(os.environ.get("MQTT_PORT", "1883"))
    except ValueError as exc:
        raise ConfigError("MQTT_PORT phải là số nguyên.") from exc
    return {
        "host": host, "port": port,
        "username": os.environ.get("MQTT_USERNAME") or None,
        "password": os.environ.get("MQTT_PASSWORD") or None,   # không bao giờ ghi vào log
        "client_id": os.environ.get("MQTT_CLIENT_ID", "app05-worker"),
    }


def handle(engine, stats: Stats, topic: str, payload: bytes, retained: bool, clock=None) -> bool:
    """Xử lý một bản tin. Trả True nếu được phép ACK (đã commit hoặc bị từ chối có chủ đích)."""
    received_at = (clock or (lambda: datetime.now(timezone.utc)))()
    try:
        with Session(engine) as db:
            result = ingest(db, topic, payload, received_at, retained)
    except SQLAlchemyError:
        stats.db_failures += 1
        log.exception("Lỗi DB khi xử lý bản tin; không ACK")
        return False
    stats.note(result.status, result.code)
    if result.status == "rejected":
        log.warning("reject %s topic=%s", result.code, topic)
    return True


def run() -> int:
    import paho.mqtt.client as mqtt

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        db_settings, cfg = Settings.from_env(), mqtt_settings()
    except ConfigError as exc:
        log.error("%s", exc)
        return 2
    engine = make_engine(db_settings.database_url, db_settings.statement_timeout_ms)
    stats = Stats()
    stop = threading.Event()
    retry = threading.Event()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cfg["client_id"], protocol=mqtt.MQTTv311,
                         clean_session=False, manual_ack=True)
    if cfg["username"]:
        client.username_pw_set(cfg["username"], cfg["password"])

    def on_connect(c, _u, _f, reason_code, _p=None):
        stats.connected = not reason_code.is_failure
        if stats.connected:
            c.subscribe(SUBSCRIBE_TOPIC, qos=1)
            log.info("đã kết nối broker và subscribe %s", SUBSCRIBE_TOPIC)
        else:
            log.error("kết nối broker thất bại: %s", reason_code)

    def on_disconnect(_c, _u, _f, _rc, _p=None):
        stats.connected = False
        log.warning("mất kết nối broker")

    def on_message(c, _u, msg):
        if handle(engine, stats, msg.topic, bytes(msg.payload), bool(msg.retain)):
            c.ack(msg.mid, msg.qos)
        else:
            retry.set()             # không ACK; vòng chính ngắt rồi nối lại để broker gửi lại các bản chưa ACK

    client.on_connect, client.on_disconnect, client.on_message = on_connect, on_disconnect, on_message
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    client.connect(cfg["host"], cfg["port"], keepalive=30)
    client.loop_start()
    try:
        while not stop.wait(1.0):
            if retry.is_set():
                # Ngắt hẳn rồi nối lại từ luồng chính (paho dừng luồng mạng sau disconnect()).
                client.disconnect()
                client.loop_stop()
                if stop.wait(RETRY_DELAY_SECONDS):
                    break
                retry.clear()
                try:
                    client.reconnect()
                except OSError:
                    log.warning("chưa kết nối lại được broker; thử lại")
                    retry.set()
                client.loop_start()
            # Mất kết nối ngoài ý muốn do luồng mạng của paho tự nối lại.
    finally:
        client.loop_stop()
        client.disconnect()
        log.info("kết thúc; thống kê: %s, db_failures=%d", dict(stats.counts), stats.db_failures)
        engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(run())
