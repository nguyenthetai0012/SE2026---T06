"""Route /api/v1/exports (BT3 VT-023). Thứ tự kiểm: xác thực -> quyền -> Idempotency-Key -> body -> scope -> tạo."""
from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from .auth import authenticate, require_export
from .config import Settings
from .errors import export_not_found, export_too_large, idempotency_conflict, invalid_query
from .exports import (
    ExportRequest, ExportTooLarge, IdempotencyConflict, PgExportStore, StoredExport, create_export, get_owned_export,
    pg_row_source,
)
from .params import parse_id, parse_ts, read_query
from .schemas import ErrorResponse, ExportCreate, ExportResponse

log = logging.getLogger("app.exports")
IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9._:-]{8,64}$")
MAX_RANGE = timedelta(days=31)
PREFIX = "/api/v1/exports"


async def _raw_body(request: Request) -> bytes:
    # Đọc body thủ công để xác thực chạy TRƯỚC khi validate body (client chưa xác thực không dò được luật validate).
    return await request.body()


def _parse_body(raw: bytes) -> ExportRequest:
    try:
        b = ExportCreate.model_validate_json(raw or b"")
    except ValidationError:
        raise invalid_query("body phải là JSON {building_id, metric, start, end}") from None
    parse_id(b.building_id, "building_id")
    start, end = parse_ts(b.start, "start"), parse_ts(b.end, "end")
    if not start < end:
        raise invalid_query("start must be earlier than end")
    if end - start > MAX_RANGE:
        raise invalid_query("khoảng thời gian export tối đa 31 ngày")
    return ExportRequest(building_id=b.building_id, metric=b.metric, start=start, end=end)


def _job(e: StoredExport) -> dict:
    url = f"{PREFIX}/{e.export_id}"
    return {"export_id": str(e.export_id), "building_id": e.building_id, "metric": e.metric, "start": e.start,
            "end": e.end, "row_count": e.row_count, "content_sha256": e.content_sha256,
            "created_at": e.created_at, "download_url": url}


def build_export_router(get_db: Callable[[], Iterator[Session]], now: Callable[[], datetime], settings: Settings,
                        err: dict) -> APIRouter:
    router = APIRouter(prefix=PREFIX, tags=["exports"])
    responses = {401: {"model": ErrorResponse, "description": "UNAUTHENTICATED"},
                 403: {"model": ErrorResponse, "description": "FORBIDDEN"},
                 404: {"model": ErrorResponse, "description": "NOT_FOUND (không tồn tại hoặc ngoài scope)"},
                 503: err[503], 500: err[500]}

    @router.post("", status_code=201, response_model=ExportResponse, responses={
        **responses, 409: {"model": ErrorResponse, "description": "IDEMPOTENCY_CONFLICT"},
        422: {"model": ErrorResponse, "description": "INVALID_QUERY hoặc EXPORT_TOO_LARGE"}},
        openapi_extra={
            "parameters": [{"name": "Idempotency-Key", "in": "header", "required": True,
                            "schema": {"type": "string", "pattern": IDEMPOTENCY_KEY_RE.pattern}}],
            "requestBody": {"required": True, "content": {"application/json": {
                "schema": ExportCreate.model_json_schema()}}}})
    def create(request: Request, response: Response, raw: bytes = Depends(_raw_body), db: Session = Depends(get_db)):
        """Tạo export CSV readings của một building trong [start,end). Retry cùng Idempotency-Key trả lại export cũ."""
        principal = require_export(authenticate(db, request.headers.get("authorization")))
        key = request.headers.get("idempotency-key", "")
        if not IDEMPOTENCY_KEY_RE.match(key):
            raise invalid_query("thiếu hoặc sai Idempotency-Key (8-64 ký tự A-Z a-z 0-9 . _ : -)")
        req = _parse_body(raw)
        if req.building_id not in principal.buildings:
            log.info("export denied client=%s reason=scope", principal.client_id)
            raise export_not_found()
        try:
            export, created = create_export(PgExportStore(db), pg_row_source(db), principal, key, req,
                                            now=now(), max_rows=settings.export_max_rows)
        except IdempotencyConflict:
            db.rollback()
            raise idempotency_conflict() from None
        except ExportTooLarge:
            db.rollback()
            raise export_too_large(settings.export_max_rows) from None
        db.commit()
        if created:
            log.info("export created client=%s building=%s rows=%d id=%s", principal.client_id, export.building_id,
                     export.row_count, export.export_id)
        else:
            response.status_code = 200
            response.headers["Idempotent-Replayed"] = "true"
        response.headers["Location"] = f"{PREFIX}/{export.export_id}"
        return {"data": _job(export), "meta": {"generated_at": now()}}

    @router.get("/{export_id:path}", response_class=Response, responses={
        **responses, 200: {"content": {"text/csv": {}}, "description": "Nội dung CSV đã lưu khi tạo"}})
    def download(export_id: str, request: Request, db: Session = Depends(get_db)):
        """Tải CSV. Chỉ client đã tạo export và building còn trong scope; còn lại 404 như không tồn tại."""
        read_query(request, set())  # như mọi GET khác: query param lạ -> 422 (không lộ gì về scope)
        principal = require_export(authenticate(db, request.headers.get("authorization")))
        try:
            eid = uuid.UUID(export_id)
        except ValueError:
            raise export_not_found() from None
        export = get_owned_export(db, principal, eid)
        if export is None:
            raise export_not_found()
        return Response(export.content, media_type="text/csv; charset=utf-8", headers={
            "Content-Disposition": f'attachment; filename="export-{export.export_id}.csv"',
            "Cache-Control": "no-store", "ETag": f'"{export.content_sha256}"', "X-Content-Type-Options": "nosniff"})

    return router
