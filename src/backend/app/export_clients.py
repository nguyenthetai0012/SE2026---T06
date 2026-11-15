"""Cấp token cho client xuất dữ liệu. Token chỉ hiện một lần; DB chỉ giữ SHA-256.

    cd src/backend && DATABASE_URL=... python -m app.export_clients --id ops --name "Ops script" \
        --building BLD-A --can-export
"""
from __future__ import annotations

import argparse
import hashlib
import secrets
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings
from .db import make_engine
from .models import Building, ExportClient, ExportClientScope
from .params import ID_RE


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_client(db: Session, *, client_id: str, name: str, buildings: list[str], can_export: bool) -> str:
    if not ID_RE.match(client_id):
        raise ValueError("client_id sai định dạng")
    known = set(db.scalars(select(Building.building_id).where(Building.building_id.in_(buildings))))
    missing = sorted(set(buildings) - known)
    if missing:
        raise ValueError(f"building không tồn tại: {', '.join(missing)}")
    token = secrets.token_urlsafe(32)
    db.add(ExportClient(client_id=client_id, name=name, token_sha256=hash_token(token), can_export=can_export))
    db.flush()
    db.add_all(ExportClientScope(client_id=client_id, building_id=b) for b in sorted(set(buildings)))
    db.commit()
    return token


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--building", action="append", required=True)
    ap.add_argument("--can-export", action="store_true")
    a = ap.parse_args(argv)
    settings = Settings.from_env()
    with Session(make_engine(settings.database_url, settings.statement_timeout_ms)) as db:
        try:
            token = issue_client(db, client_id=a.id, name=a.name, buildings=a.building, can_export=a.can_export)
        except ValueError as exc:
            print(f"lỗi: {exc}", file=sys.stderr)
            return 1
    # In ra stdout đúng một lần để người vận hành lưu; không ghi log.
    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
