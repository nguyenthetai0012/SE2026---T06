"""Finite synthetic MQTT readings for the APP-05 MVP."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import random
import re
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = ROOT / "src/backend/seed/registry.json"
MODES = ("normal", "duplicate", "invalid", "late", "out-of-order", "offline", "load")
ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")


def read_registry(path):
    registry = json.loads(Path(path).read_text(encoding="utf-8"))
    buildings = {b["building_id"] for b in registry["buildings"]}
    devices = [d for d in registry["devices"] if d["enabled"]]
    ids = set()
    for d in devices:
        if (d["building_id"] not in buildings or not ID_PATTERN.fullmatch(d["building_id"])
                or not ID_PATTERN.fullmatch(d["device_id"]) or d["device_id"] in ids
                or d["period_seconds"] != 60):
            raise ValueError("Registry must contain unique enabled devices with valid IDs and 60-second periods")
        ids.add(d["device_id"])
    if not devices:
        raise ValueError("Registry has no enabled devices")
    return sorted(devices, key=lambda d: (d["building_id"], d["device_id"]))


def stamp(value):
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def generate(devices, mode, seed, start, cycles):
    """Yield one list of (topic, bytes, logical-new) per simulated minute."""
    if mode == "offline" and (cycles < 5 or not any(d["device_id"] == "A-02" for d in devices)):
        raise ValueError("offline requires A-02 and at least 5 cycles")
    if mode == "out-of-order" and cycles < 2:
        raise ValueError("out-of-order requires at least 2 cycles")
    order = list(range(cycles))
    if mode == "out-of-order":
        order[0], order[1] = order[1], order[0]
    for cycle, slot in enumerate(order):
        batch = []
        for device in devices:
            if mode == "offline" and device["device_id"] == "A-02" and 1 <= cycle <= 3:
                continue
            event = start + timedelta(minutes=slot + 1)
            if mode == "late":
                event -= timedelta(hours=1)
            power = round(random.Random(f"{seed}|{device['device_id']}|{stamp(event)}").uniform(3, 12), 3)
            for metric, value in (("power_kw", power), ("energy_kwh", round(power / 60, 9))):
                topic = f"campus/v1/{device['building_id']}/{device['device_id']}/readings"
                identity = f"{seed}|{stamp(event)}|{device['building_id']}|{device['device_id']}|{metric}"
                payload = {"schema_version": "1.0", "message_id": str(uuid.uuid5(uuid.NAMESPACE_URL, identity)),
                           "building_id": device["building_id"], "device_id": device["device_id"],
                           "event_time": stamp(event), "metric": metric, "value": value}
                if metric == "energy_kwh":
                    payload["interval_start"] = stamp(event - timedelta(minutes=1))
                variant = (cycle * len(devices) * 2 + len(batch)) % 6
                if mode == "invalid":
                    if variant == 0:
                        del payload["value"]
                    elif variant == 1:
                        payload["value"] = str(value)
                    elif variant == 2:
                        payload["event_time"] = "not-a-timestamp"
                    elif variant == 3:
                        payload["device_id"] = "UNKNOWN"
                    elif variant == 4:
                        topic = f"campus/v1/WRONG/{device['device_id']}/readings"
                raw = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode()
                if mode == "invalid" and variant == 5:
                    raw += b" " * (4097 - len(raw))
                batch.append((topic, raw, True))
                if mode == "duplicate":
                    batch.append((topic, raw, False))
        yield batch


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES, default="normal")
    parser.add_argument("--cycles", type=int, required=True, help="finite number of one-minute intervals")
    parser.add_argument("--seed", type=int, default=int(os.getenv("SIM_SEED", "1")))
    parser.add_argument("--start", help="UTC interval start, ISO 8601 with Z; use for reproducibility")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--devices", type=int, help="use the first N enabled registry devices")
    parser.add_argument("--rate", type=float, default=10, help="load mode publish attempts per second")
    parser.add_argument("--host", default=os.getenv("MQTT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.cycles <= 10000 or not 0 < args.rate <= 10000 or not 1 <= args.port <= 65535:
        parser.error("cycles, rate or port out of range")
    try:
        devices = read_registry(args.registry)
        if args.devices is not None:
            if not 1 <= args.devices <= len(devices):
                raise ValueError("devices must be within the enabled registry size")
            devices = devices[:args.devices]
        if args.start:
            if not args.start.endswith("Z"):
                raise ValueError("start must be UTC with Z")
            start = datetime.fromisoformat(args.start.replace("Z", "+00:00"))
            if start.second or start.microsecond:
                raise ValueError("start must be on a UTC minute boundary")
        else:
            start = datetime.now(timezone.utc).replace(second=0, microsecond=0) - timedelta(minutes=args.cycles)
        if start + timedelta(minutes=args.cycles) > datetime.now(timezone.utc):
            raise ValueError("last event cannot be in the future")
        batches = list(generate(devices, args.mode, args.seed, start, args.cycles))
    except (ValueError, KeyError, OSError, TypeError) as exc:
        parser.error(str(exc))
    client = None
    logical = attempts = 0
    try:
        if not args.dry_run:
            import paho.mqtt.client as mqtt
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv311)
            if os.getenv("MQTT_USERNAME"):
                client.username_pw_set(os.environ["MQTT_USERNAME"], os.getenv("MQTT_PASSWORD"))
            client.connect(args.host, args.port, keepalive=60)
            client.loop_start()
        print(f"mode={args.mode} seed={args.seed} start={stamp(start)} cycles={args.cycles} devices={len(devices)}")
        for index, batch in enumerate(batches):
            if index and not args.dry_run and args.mode != "load":
                time.sleep(60)
            for topic, raw, fresh in batch:
                if args.dry_run:
                    print(topic, raw.decode())
                else:
                    result = client.publish(topic, raw, qos=1, retain=False)
                    result.wait_for_publish(timeout=10)
                    if not result.is_published():
                        raise RuntimeError("MQTT publish timed out")
                    if args.mode == "load":
                        time.sleep(1 / args.rate)
                attempts += 1
                logical += int(fresh)
        print(f"logical_messages={logical} publish_attempts={attempts}")
    finally:
        if client:
            client.disconnect()
            client.loop_stop()


if __name__ == "__main__":
    main()
