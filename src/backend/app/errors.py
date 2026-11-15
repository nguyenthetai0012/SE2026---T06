"""Envelope lỗi thống nhất: {"error":{"code","message","request_id"}} (docs/contracts/mvp-api.md)."""
from __future__ import annotations


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict[str, str] | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.headers = headers or {}


def invalid_query(message: str) -> ApiError:
    return ApiError(422, "INVALID_QUERY", message)


def filter_mismatch(message: str) -> ApiError:
    return ApiError(422, "FILTER_MISMATCH", message)


def invalid_cursor() -> ApiError:
    return ApiError(422, "INVALID_CURSOR", "cursor không hợp lệ hoặc không khớp với truy vấn hiện tại")


def not_found(message: str) -> ApiError:
    return ApiError(404, "NOT_FOUND", message)


# Cùng một thông điệp cho "không có" và "không được phép" để không lộ building/export nào tồn tại.
EXPORT_SCOPE_MESSAGE = "không có tài nguyên này trong phạm vi được cấp"


def export_not_found() -> ApiError:
    return ApiError(404, "NOT_FOUND", EXPORT_SCOPE_MESSAGE)


def idempotency_conflict() -> ApiError:
    return ApiError(409, "IDEMPOTENCY_CONFLICT", "Idempotency-Key đã dùng cho một yêu cầu khác")


def export_too_large(limit: int) -> ApiError:
    return ApiError(422, "EXPORT_TOO_LARGE", f"export vượt quá {limit} dòng; thu hẹp khoảng thời gian")
