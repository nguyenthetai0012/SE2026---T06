"""Xác thực client xuất dữ liệu bằng bearer token (chỉ cho /exports; các API đọc MVP giữ nguyên không xác thực)."""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from .errors import ApiError
from .export_clients import hash_token
from .exports import Principal
from .models import ExportClient, ExportClientScope

TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{20,128}$")


def unauthenticated() -> ApiError:
    return ApiError(401, "UNAUTHENTICATED", "cần bearer token hợp lệ", headers={"WWW-Authenticate": "Bearer"})


def forbidden() -> ApiError:
    return ApiError(403, "FORBIDDEN", "client không có quyền xuất dữ liệu")


def authenticate(db: Session, authorization: str | None) -> Principal:
    """Token thiếu, sai định dạng, không tồn tại hoặc client bị tắt đều trả cùng một lỗi 401."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not TOKEN_RE.match(token):
        raise unauthenticated()
    row = db.execute(
        select(ExportClient.client_id, ExportClient.can_export, ExportClient.enabled)
        .where(ExportClient.token_sha256 == hash_token(token))
    ).first()
    if row is None or not row.enabled:
        raise unauthenticated()
    buildings = frozenset(db.scalars(select(ExportClientScope.building_id)
                                     .where(ExportClientScope.client_id == row.client_id)))
    return Principal(client_id=row.client_id, can_export=row.can_export, buildings=buildings)


def require_export(principal: Principal) -> Principal:
    if not principal.can_export:
        raise forbidden()
    return principal
