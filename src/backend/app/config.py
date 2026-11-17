"""Cấu hình đọc từ biến môi trường. Giá trị demo lấy từ docs/decisions/mvp-baseline.md (đề xuất, đổi qua PR)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

# Cấu hình demo của baseline (không phải SLA).
OFFLINE_MULTIPLIER = 3      # offline và data_stale cùng biên: >= 3 * period
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    database_url: str
    statement_timeout_ms: int = 8000
    cors_origins: tuple[str, ...] = field(default_factory=tuple)

    @staticmethod
    def from_env() -> "Settings":
        url = os.environ.get("DATABASE_URL", "").strip()
        if not url:
            # Fail rõ, không có mặc định chứa mật khẩu.
            raise ConfigError("Thiếu biến môi trường DATABASE_URL (xem src/backend/.env.example).")
        try:
            timeout = int(os.environ.get("DB_STATEMENT_TIMEOUT_MS", "8000"))
        except ValueError as exc:
            raise ConfigError("DB_STATEMENT_TIMEOUT_MS phải là số nguyên (ms).") from exc
        if timeout <= 0:
            raise ConfigError("DB_STATEMENT_TIMEOUT_MS phải > 0.")
        origins = tuple(o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip())
        if "*" in origins:
            raise ConfigError("CORS_ORIGINS không được dùng wildcard.")
        return Settings(database_url=url, statement_timeout_ms=timeout, cors_origins=origins)
