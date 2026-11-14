"""Test worker qua broker Mosquitto thật (issue #37): publish QoS 1 -> worker.consumer -> PostgreSQL.

Cần lệnh `mosquitto` trong PATH. Thiếu broker thì bỏ qua với lý do rõ; đặt REQUIRE_MQTT_BROKER=1 (ví dụ trong CI) để
biến việc thiếu broker thành lỗi. Broker chỉ nghe 127.0.0.1 trên cổng tự chọn, ẩn danh, không lưu đĩa.
Kịch bản DB dừng giữa chừng chưa tự động hóa (đã chạy tay, xem src/backend/README.md).
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

BACKEND = Path(__file__).resolve().parents[3] / "src" / "backend"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def broker(tmp_path_factory):
    exe = shutil.which("mosquitto")
    if exe is None:
        if os.environ.get("REQUIRE_MQTT_BROKER") == "1":
            pytest.fail("Thiếu lệnh mosquitto nhưng REQUIRE_MQTT_BROKER=1")
        pytest.skip("không có lệnh mosquitto trong PATH (đặt REQUIRE_MQTT_BROKER=1 để coi là lỗi)")
    port = _free_port()
    conf = tmp_path_factory.mktemp("mosq") / "mosquitto.conf"
    conf.write_text(f"listener {port} 127.0.0.1\nallow_anonymous true\npersistence false\n")
    proc = subprocess.Popen([exe, "-c", str(conf)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    else:
        proc.kill()
        pytest.fail("mosquitto không mở cổng")
    yield port
    proc.terminate()
    proc.wait(timeout=5)


class Worker:
    def __init__(self, port: int, database_url: str):
        self.env = {**os.environ, "DATABASE_URL": database_url, "MQTT_HOST": "127.0.0.1", "MQTT_PORT": str(port),
                    "MQTT_CLIENT_ID": f"test-{uuid.uuid4().hex[:8]}", "PYTHONPATH": str(BACKEND)}
        self.proc: subprocess.Popen | None = None
        self.log = ""

    def start(self):
        self.proc = subprocess.Popen([sys.executable, "-m", "worker.consumer"], cwd=BACKEND, env=self.env,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        time.sleep(2.0)             # chờ kết nối + subscribe
        assert self.proc.poll() is None, "worker thoát sớm"

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.log += self.proc.communicate(timeout=10)[0] or ""
            except subprocess.TimeoutExpired:
                self.proc.kill()
        return self.log


@pytest.fixture()
def worker(broker, database_url, db):
    w = Worker(broker, database_url)
    yield w
    w.stop()


def publish(port, messages, client_id=None):
    import paho.mqtt.client as mqtt
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id or f"pub-{uuid.uuid4().hex[:8]}",
                    protocol=mqtt.MQTTv311)
    c.connect("127.0.0.1", port)
    c.loop_start()
    for topic, body, retain in messages:
        c.publish(topic, body if isinstance(body, (bytes, str)) else json.dumps(body), qos=1, retain=retain).wait_for_publish()
    c.loop_stop()
    c.disconnect()


def msg(device="A-01", building="BLD-A", metric="power_kw", value=5, **extra):
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    p = {"schema_version": "1.0", "message_id": str(uuid.uuid4()), "building_id": building, "device_id": device,
         "event_time": now, "metric": metric, "value": value}
    p.update(extra)
    return p


def topic(p):
    return f"campus/v1/{p['building_id']}/{p['device_id']}/readings"


def wait_for(engine, sql, expected, timeout=10.0):
    end = time.time() + timeout
    got = None
    while time.time() < end:
        with engine.connect() as c:
            got = c.execute(text(sql)).scalar()
        if got == expected:
            return got
        time.sleep(0.2)
    return got


def test_live_valid_duplicate_conflict_and_invalid(worker, broker, engine):
    worker.start()
    ok = msg(value=12)
    other = msg(device="B-01", building="BLD-B", value=3)
    publish(broker, [
        (topic(ok), ok, False), (topic(ok), ok, False),                         # duplicate
        (topic(ok), {**ok, "value": 13}, False),                                # MESSAGE_ID_CONFLICT
        (topic(other), other, False),
        (topic(ok), b'{"bad"', False),                                          # INVALID_JSON
        (topic(ok), {**msg(), "value": "5"}, False),                            # INVALID_VALUE
        ("campus/v1/BLD-B/A-01/readings", msg(), False),                        # TOPIC_MISMATCH
    ])
    assert wait_for(engine, "select count(*) from readings", 2) == 2
    assert wait_for(engine, "select count(*) from alerts", 1) == 1               # 12 kW > 10 kW, chỉ một lần
    assert wait_for(engine, f"select value from readings where message_id='{ok['message_id']}'", 12) == 12
    log = worker.stop()
    for code in ("MESSAGE_ID_CONFLICT", "INVALID_JSON", "INVALID_VALUE", "TOPIC_MISMATCH"):
        assert log.count(f"reject {code}") == 1, log
    assert "'duplicate': 1" in log and "'accepted': 2" in log, log        # thống kê in khi worker thoát


def test_live_message_sent_while_worker_down_is_delivered_after_restart(worker, broker, engine):
    worker.start()
    worker.stop()                                   # broker giữ session bền theo MQTT_CLIENT_ID cố định
    m = msg(device="B-01", building="BLD-B", value=2)
    publish(broker, [(topic(m), m, False)])
    assert wait_for(engine, "select count(*) from readings", 0, timeout=1.5) == 0
    worker.start()
    assert wait_for(engine, "select count(*) from readings", 1) == 1


def test_live_retained_message_rejected_on_subscribe(worker, broker, engine):
    m = msg(value=4)
    publish(broker, [(topic(m), m, True)])           # lưu retained trước khi worker subscribe
    worker.start()
    assert wait_for(engine, "select count(*) from readings", 0, timeout=2.0) == 0
    assert "reject RETAINED_MESSAGE" in worker.stop()
