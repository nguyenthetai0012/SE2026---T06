"""Envelope lỗi thống nhất: {"error":{"code","message","request_id"}} (docs/contracts/mvp-api.md)."""
from __future__ import annotations


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def invalid_query(message: str) -> ApiError:
    return ApiError(422, "INVALID_QUERY", message)


def filter_mismatch(message: str) -> ApiError:
    return ApiError(422, "FILTER_MISMATCH", message)


def invalid_cursor() -> ApiError:
    return ApiError(422, "INVALID_CURSOR", "cursor không hợp lệ hoặc không khớp với truy vấn hiện tại")


def not_found(message: str) -> ApiError:
    return ApiError(404, "NOT_FOUND", message)
