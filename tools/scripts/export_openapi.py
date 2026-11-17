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
# Thông báo in ra chỉ dùng ASCII (kể cả đường dẫn, lấy tương đối theo repo): trên Windows cp1252, stdout bị
# pipe/redirect sẽ crash UnicodeEncodeError với ký tự tiếng Việt.
REL = OUT.relative_to(ROOT).as_posix()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    app = create_app(Settings(database_url="postgresql+psycopg://openapi@localhost/none"))
    text = json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUT.exists() or json.loads(OUT.read_text(encoding="utf-8")) != json.loads(text):
            print(f"{REL} is out of date with the app; rerun this script without --check.", file=sys.stderr)
            return 1
        print(f"{REL} matches the app")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {REL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
