"""FastAPI app: HTTP API đọc dữ liệu MVP (base /api/v1)."""
from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Callable, Iterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import queries
from .config import Settings
from .db import make_engine
from .errors import ApiError
from .params import parse_id, parse_limit, parse_metric, parse_range, read_query
from .schemas import (
    AlertListResponse, DeviceListResponse, ErrorResponse, HistoryResponse, ReadyResponse, SummaryResponse,
)

log = logging.getLogger("app")
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
# Mô tả viết tường minh: tên chuẩn của mã 422 khác nhau giữa Python 3.12 và 3.13, làm OpenAPI không ổn định.
ERR = {
    404: {"model": ErrorResponse, "description": "NOT_FOUND"},
    422: {"model": ErrorResponse, "description": "INVALID_QUERY, FILTER_MISMATCH hoặc INVALID_CURSOR"},
    503: {"model": ErrorResponse, "description": "DEPENDENCY_UNAVAILABLE"},
}


def _error(request: Request, status: int, code: str, message: str) -> JSONResponse:
    rid = getattr(request.state, "request_id", None) or uuid.uuid4().hex
    return JSONResponse({"error": {"code": code, "message": message, "request_id": rid}}, status_code=status,
                        headers={"X-Request-ID": rid})


def create_app(settings: Settings | None = None, clock: Callable[[], datetime] | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    now_fn = clock or (lambda: datetime.now(timezone.utc))
    engine = make_engine(settings.database_url, settings.statement_timeout_ms)

    app = FastAPI(title="APP-05 Smart Campus Energy Dashboard API", version="1.0.0",
                  description="HTTP API đọc dữ liệu MVP. Contract: docs/contracts/mvp-api.md (baseline PROPOSED).")
    app.state.engine = engine

    if settings.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["GET"], allow_headers=["X-Request-ID"])

    @app.middleware("http")
    async def request_id_mw(request: Request, call_next):
        supplied = request.headers.get("x-request-id", "")
        request.state.request_id = supplied if REQUEST_ID_RE.match(supplied) else uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return _error(request, exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        return _error(request, 422, "INVALID_QUERY", "yêu cầu không hợp lệ")

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return _error(request, 404, "NOT_FOUND", "đường dẫn không tồn tại")
        return _error(request, exc.status_code, "INVALID_QUERY", "yêu cầu không được hỗ trợ")

    @app.exception_handler(OperationalError)
    async def _db_down(request: Request, exc: OperationalError):
        log.error("database unavailable: %s", type(exc.orig).__name__)  # không log câu SQL/tham số
        return _error(request, 503, "DEPENDENCY_UNAVAILABLE", "cơ sở dữ liệu tạm thời không khả dụng")

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.error("unhandled error: %s", type(exc).__name__)
        return _error(request, 500, "INTERNAL_ERROR", "lỗi nội bộ")

    def get_db() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    def now() -> datetime:
        return now_fn()

    router = APIRouter(prefix="/api/v1")

    @router.get("/buildings/summary", response_model=SummaryResponse, responses=ERR, tags=["buildings"])
    def buildings_summary(request: Request, db: Session = Depends(get_db)):
        """Tổng điện năng ghi nhận theo tòa nhà trong [start,end]; query: start, end (bắt buộc), building_id."""
        q = read_query(request, {"start", "end", "building_id"})
        start, end = parse_range(q)
        building_id = parse_id(q["building_id"], "building_id") if "building_id" in q else None
        generated_at = now()
        data = queries.building_summary(db, start, end, building_id, generated_at)
        return {"data": data, "meta": {"generated_at": generated_at, "start": start, "end": end,
                                       "building_id": building_id, "next_cursor": None}}

    @router.get("/devices", response_model=DeviceListResponse, responses=ERR, tags=["devices"])
    def devices(request: Request, db: Session = Depends(get_db)):
        """Danh sách thiết bị; query: building_id, limit, cursor."""
        q = read_query(request, {"building_id", "limit", "cursor"})
        building_id = parse_id(q["building_id"], "building_id") if "building_id" in q else None
        limit = parse_limit(q)
        generated_at = now()
        data, nxt = queries.list_devices(db, building_id, limit, q.get("cursor"), generated_at)
        return {"data": data, "meta": {"generated_at": generated_at, "building_id": building_id, "next_cursor": nxt}}

    @router.get("/devices/{device_id}/readings", response_model=HistoryResponse, responses=ERR, tags=["devices"])
    def device_readings(device_id: str, request: Request, db: Session = Depends(get_db)):
        """Lịch sử reading theo event_time trong [start,end); query: metric, start, end (bắt buộc), limit, cursor."""
        parse_id(device_id, "device_id")
        q = read_query(request, {"metric", "start", "end", "limit", "cursor"})
        metric = parse_metric(q)
        start, end = parse_range(q)
        limit = parse_limit(q)
        generated_at = now()
        data, nxt = queries.device_history(db, device_id, metric, start, end, limit, q.get("cursor"))
        return {"data": data, "meta": {"generated_at": generated_at, "device_id": device_id, "metric": metric,
                                       "start": start, "end": end, "next_cursor": nxt}}

    @router.get("/alerts", response_model=AlertListResponse, responses=ERR, tags=["alerts"])
    def alerts(request: Request, db: Session = Depends(get_db)):
        """Cảnh báo (chỉ đọc); query: building_id, device_id, limit, cursor."""
        q = read_query(request, {"building_id", "device_id", "limit", "cursor"})
        building_id = parse_id(q["building_id"], "building_id") if "building_id" in q else None
        device_id = parse_id(q["device_id"], "device_id") if "device_id" in q else None
        limit = parse_limit(q)
        generated_at = now()
        data, nxt = queries.list_alerts(db, building_id, device_id, limit, q.get("cursor"))
        return {"data": data, "meta": {"generated_at": generated_at, "building_id": building_id,
                                       "device_id": device_id, "next_cursor": nxt}}

    @router.get("/health/ready", response_model=ReadyResponse, responses={503: ERR[503]}, tags=["health"])
    def ready(request: Request, db: Session = Depends(get_db)):
        """200 khi DB truy cập được; DB lỗi -> 503. Không phản ánh sức khỏe worker."""
        read_query(request, set())
        db.execute(text("SELECT 1"))
        return {"data": {"status": "ready"}, "meta": {"generated_at": now()}}

    app.include_router(router)
    return app
