from __future__ import annotations

from sqlalchemy import Engine, create_engine


def make_engine(database_url: str, statement_timeout_ms: int = 8000) -> Engine:
    """Engine với timezone UTC và statement_timeout (truy vấn quá hạn -> 503, không thành 'rỗng')."""
    options = f"-c timezone=UTC -c statement_timeout={int(statement_timeout_ms)}"
    # READ COMMITTED được ghim, không dựa vào mặc định của DB/role: guard idempotency của /exports cần câu
    # đọc lại sau ON CONFLICT thấy bản ghi vừa commit (REPEATABLE READ -> 503, đo ở BT3 AI review #6).
    return create_engine(database_url, pool_pre_ping=True, isolation_level="READ COMMITTED",
                         connect_args={"options": options})
