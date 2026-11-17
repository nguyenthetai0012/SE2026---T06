from __future__ import annotations

from sqlalchemy import Engine, create_engine


def make_engine(database_url: str, statement_timeout_ms: int = 8000) -> Engine:
    """Engine với timezone UTC và statement_timeout (truy vấn quá hạn -> 503, không thành 'rỗng')."""
    options = f"-c timezone=UTC -c statement_timeout={int(statement_timeout_ms)}"
    return create_engine(database_url, pool_pre_ping=True, connect_args={"options": options})
