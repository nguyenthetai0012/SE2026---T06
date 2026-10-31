#!/usr/bin/env python3
"""Xuất OpenAPI từ model FastAPI thực hiện ra docs/contracts/mvp-openapi.json.

    python tools/scripts/export_openapi.py          # ghi file
    python tools/scripts/export_openapi.py --check  # lỗi (exit 1) nếu file đã commit bị lệch
Không cần kết nối DB (engine chỉ kết nối khi có request)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "backend"))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

OUT = ROOT / "docs" / "contracts" / "mvp-openapi.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    app = create_app(Settings(database_url="postgresql+psycopg://openapi@localhost/none"))
    text = json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUT.exists() or json.loads(OUT.read_text(encoding="utf-8")) != json.loads(text):
            print(f"{OUT} lệch với app; chạy lại script không kèm --check.", file=sys.stderr)
            return 1
        print("openapi khớp")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"đã ghi {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
