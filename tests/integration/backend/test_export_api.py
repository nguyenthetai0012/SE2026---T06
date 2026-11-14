"""BT3 VT-023: API xuất dữ liệu có phân quyền và giới hạn phạm vi.

Kỹ thuật thiết kế test: decision table. Mỗi bảng ghi điều kiện -> hành động; mỗi cột (rule) là một test.
Chạy trên PostgreSQL thật dựng bằng Alembic (risk: mock che giấu contract sai với database).

Bảng DT-C (POST /exports). Điều kiện kiểm theo thứ tự; "-" = không quan tâm.
| Rule | Token hợp lệ | Client enabled | can_export | Building trong scope | Building tồn tại | Body/range hợp lệ | Kết quả |
| C1   | thiếu        | -              | -          | -                    | -                | -                 | 401     |
| C2   | sai/lạ       | -              | -          | -                    | -                | -                 | 401     |
| C3   | đúng         | không          | -          | -                    | -                | -                 | 401     |
| C4   | đúng         | có             | không      | có                   | có               | có                | 403     |
| C5   | đúng         | có             | có         | không                | có               | có                | 404     |
| C6   | đúng         | có             | có         | không                | không            | có                | 404     |
| C7   | đúng         | có             | có         | có                   | có               | không             | 422     |
| C8   | đúng         | có             | có         | có                   | có               | có                | 201     |
"""
from __future__ import annotations

import logging
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pytest
from export_helpers import (
    CSV_HEADER, END, EXPORTS, START, count_exports, headers, make_client, oracle_rows, parse_csv, post,
)
from fastapi.testclient import TestClient
from loader import add_reading, load_fixture
from sqlalchemy import text

from app.config import Settings
from app.main import create_app


@pytest.fixture()
def exp_db(db):
    db.execute(text("TRUNCATE export_clients RESTART IDENTITY CASCADE"))
    db.commit()
    return db


@pytest.fixture()
def tokens(exp_db, fixture_data):
    load_fixture(exp_db, fixture_data)
    return {
        "ops": make_client(exp_db, "ops", ["BLD-A"]),
        "reader": make_client(exp_db, "reader", ["BLD-A"], can_export=False),
        "off": make_client(exp_db, "off", ["BLD-A"], enabled=False),
        "other": make_client(exp_db, "other", ["BLD-A", "BLD-B"]),
    }


def err(r):
    return r.json()["error"]["code"]


ROUTER_404 = "đường dẫn không tồn tại"


def assert_denied_404(r):
    """404 phải do logic phân quyền trả về, không phải router (route chưa tồn tại cũng trả 404).
    Thêm sau lần RED 2: không có kiểm tra này, các rule 404 pass ngay khi endpoint chưa được viết."""
    assert r.status_code == 404, r.text
    assert r.json()["error"]["code"] == "NOT_FOUND" and r.json()["error"]["message"] != ROUTER_404, r.text


# ---------------------------------------------------------------- DT-C: tạo export
@pytest.mark.parametrize("rule,who,raw_auth,override,status,code", [
    ("C1", None, None, {}, 401, "UNAUTHENTICATED"),
    ("C1b", None, "Basic dXNlcjpwYXNz", {}, 401, "UNAUTHENTICATED"),
    ("C1c", None, None, {"start": "not-a-time"}, 401, "UNAUTHENTICATED"),        # chưa xác thực thì không validate body
    ("C2", None, "Bearer AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", {}, 401, "UNAUTHENTICATED"),
    ("C3", "off", None, {}, 401, "UNAUTHENTICATED"),
    ("C4", "reader", None, {}, 403, "FORBIDDEN"),
    ("C5", "ops", None, {"building_id": "BLD-B"}, 404, "NOT_FOUND"),
    ("C6", "ops", None, {"building_id": "BLD-Z"}, 404, "NOT_FOUND"),
    ("C7", "ops", None, {"start": END, "end": START}, 422, "INVALID_QUERY"),
    ("C7b", "ops", None, {"start": "2026-10-01T00:00:00Z", "end": "2026-11-01T00:00:01Z"}, 422, "INVALID_QUERY"),
    ("C7c", "ops", None, {"metric": "voltage"}, 422, "INVALID_QUERY"),
    ("C7d", "ops", None, {"extra": "x"}, 422, "INVALID_QUERY"),
    ("C8", "ops", None, {}, 201, None),
])
def test_create_decision_table(client, tokens, exp_db, rule, who, raw_auth, override, status, code):
    r = post(client, tokens.get(who), raw_auth=raw_auth, **override)
    assert r.status_code == status, (rule, r.text)
    if status == 404:
        assert_denied_404(r)
    if code:
        assert err(r) == code, rule
        assert count_exports(exp_db) == 0, f"{rule}: lỗi không được để lại export"
    if status == 401:
        assert r.headers["WWW-Authenticate"] == "Bearer"


def test_out_of_scope_and_missing_building_are_indistinguishable(client, tokens):
    ra = post(client, tokens["ops"], key="key-scope-0001", building_id="BLD-B")
    rb = post(client, tokens["ops"], key="key-scope-0002", building_id="BLD-Z")
    assert_denied_404(ra), assert_denied_404(rb)
    a, b = ra.json()["error"], rb.json()["error"]
    assert (a["code"], a["message"]) == (b["code"], b["message"])           # không lộ BLD-B có tồn tại


def test_range_of_exactly_31_days_is_allowed(client, tokens):
    r = post(client, tokens["ops"], start="2026-10-01T00:00:00Z", end="2026-11-01T00:00:00Z")
    assert r.status_code == 201, r.text


def test_created_export_contains_only_scoped_rows_matching_oracle(client, tokens, exp_db):
    r = post(client, tokens["ops"])
    assert r.status_code == 201
    job = r.json()["data"]
    assert r.headers["Location"] == f"{EXPORTS}/{job['export_id']}" == job["download_url"]
    expected = oracle_rows("BLD-A", "power_kw", START, END)
    assert job["row_count"] == len(expected) == 4
    rows = parse_csv(client.get(job["download_url"], headers=headers(tokens["ops"])).content)
    assert rows[0] == CSV_HEADER and rows[1:] == expected
    assert {row[2] for row in rows[1:]} == {"BLD-A"}                         # không có BLD-B


# ---------------------------------------------------------------- DT-D: tải export
# | Rule | Token hợp lệ+enabled | can_export | Export tồn tại | Của chính client | Building còn trong scope | Kết quả |
# | D1   | không                | -          | -              | -                | -                        | 401     |
# | D2   | có                   | không      | -              | -                | -                        | 403     |
# | D3   | có                   | có         | không          | -                | -                        | 404     |
# | D4   | có                   | có         | có             | không            | có                       | 404     |
# | D5   | có                   | có         | có             | có               | không                    | 404     |
# | D6   | có                   | có         | có             | có               | có                       | 200     |
@pytest.fixture()
def created(client, tokens):
    r = post(client, tokens["ops"])
    assert r.status_code == 201
    return r.json()["data"]


def test_download_D6_owner_gets_exact_bytes(client, tokens, created):
    r = client.get(created["download_url"], headers=headers(tokens["ops"]))
    assert r.status_code == 200
    assert r.headers["content-type"] == "text/csv; charset=utf-8"
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["etag"] == f'"{created["content_sha256"]}"'
    assert "attachment" in r.headers["content-disposition"]
    import hashlib
    assert hashlib.sha256(r.content).hexdigest() == created["content_sha256"]


@pytest.mark.parametrize("rule,mutate,who,status", [
    ("D1", None, None, 401),
    ("D1b", "UPDATE export_clients SET enabled=false WHERE client_id='ops'", "ops", 401),
    ("D2", "UPDATE export_clients SET can_export=false WHERE client_id='ops'", "ops", 403),
    ("D4", None, "other", 404),                                                 # BOLA: client khác cùng scope
    ("D5", "DELETE FROM export_client_scopes WHERE client_id='ops'", "ops", 404),  # bị thu hồi scope sau khi tạo
])
def test_download_decision_table(client, tokens, exp_db, created, rule, mutate, who, status):
    if mutate:
        exp_db.execute(text(mutate))
        exp_db.commit()
    r = client.get(created["download_url"], headers=headers(tokens.get(who)))
    assert r.status_code == status, rule
    if status == 404:
        assert_denied_404(r)
    assert "message_id" not in r.text                                           # không rò nội dung CSV


@pytest.mark.parametrize("export_id", ["00000000-0000-4000-8000-000000000000", "not-a-uuid", "..%2F..%2Fetc"])
def test_download_D3_unknown_export(client, tokens, export_id):
    assert_denied_404(client.get(f"{EXPORTS}/{export_id}", headers=headers(tokens["ops"])))


# ---------------------------------------------------------------- DT-I: idempotency
# | Rule | Key hợp lệ | Key đã có (cùng client) | Cùng request | Kết quả                       |
# | I1   | không      | -                       | -            | 422, không tạo                 |
# | I2   | có         | không                   | -            | 201, tạo 1                     |
# | I3   | có         | có                      | có           | 200 replay, cùng export_id     |
# | I4   | có         | có                      | không        | 409 IDEMPOTENCY_CONFLICT       |
# | I5   | có         | có (client khác)        | -            | 201 độc lập                    |
@pytest.mark.parametrize("key", [None, "short", "x" * 65, "bad key with spaces"])
def test_idempotency_I1_invalid_key(client, tokens, exp_db, key):
    r = post(client, tokens["ops"], key=key)
    assert r.status_code == 422 and err(r) == "INVALID_QUERY"
    assert count_exports(exp_db) == 0


def test_idempotency_I3_replay_returns_same_export(client, tokens, exp_db):
    first = post(client, tokens["ops"], key="key-replay-0001")
    second = post(client, tokens["ops"], key="key-replay-0001")
    assert (first.status_code, second.status_code) == (201, 200)
    assert second.headers["Idempotent-Replayed"] == "true"
    assert second.json()["data"] == first.json()["data"]
    assert count_exports(exp_db) == 1


def test_idempotency_I4_same_key_different_request_conflicts(client, tokens, exp_db):
    assert post(client, tokens["ops"], key="key-conflict-01").status_code == 201
    r = post(client, tokens["ops"], key="key-conflict-01", end="2026-10-27T00:02:00Z")
    assert r.status_code == 409 and err(r) == "IDEMPOTENCY_CONFLICT"
    assert count_exports(exp_db) == 1


def test_idempotency_I5_key_is_scoped_per_client(client, tokens, exp_db):
    a = post(client, tokens["ops"], key="key-shared-0001")
    b = post(client, tokens["other"], key="key-shared-0001")
    assert (a.status_code, b.status_code) == (201, 201)
    assert a.json()["data"]["export_id"] != b.json()["data"]["export_id"]


@pytest.mark.parametrize("n", [30])
def test_idempotency_concurrent_retries_create_exactly_one(client, tokens, exp_db, n):
    """Failure path gắn với risk: client retry đồng thời. Chỉ DB thật mới chứng minh được guard."""
    barrier = threading.Barrier(n)

    def go(_):
        barrier.wait()
        return post(client, tokens["ops"], key="key-concurrent-01")

    with ThreadPoolExecutor(n) as ex:
        rs = list(ex.map(go, range(n)))
    codes = Counter(r.status_code for r in rs)
    assert codes == {201: 1, 200: n - 1}, codes
    assert len({r.json()["data"]["export_id"] for r in rs}) == 1
    assert count_exports(exp_db) == 1


# ---------------------------------------------------------------- contract với DB thật / failure path
def test_csv_keeps_database_decimal_and_time_precision(client, exp_db):
    token = make_client(exp_db, "ops", ["BLD-A"])
    add_reading(exp_db, message_id="00000000-0000-4000-8000-00000000e001", device_id="A-01", metric="power_kw",
                event_time="2026-10-27T00:00:30.500000Z", received_at="2026-10-27T00:00:31Z", value="0.000000001")
    add_reading(exp_db, message_id="00000000-0000-4000-8000-00000000e002", device_id="A-02", metric="power_kw",
                event_time="2026-10-27T00:00:40Z", received_at="2026-10-27T00:00:41Z", value="123456789012345.123456789")
    exp_db.commit()
    job = post(client, token).json()["data"]
    rows = parse_csv(client.get(job["download_url"], headers=headers(token)).content)
    assert [(r[4], r[7]) for r in rows[1:]] == [("2026-10-27T00:00:30.500000Z", "0.000000001"),
                                                ("2026-10-27T00:00:40Z", "123456789012345.123456789")]


def test_csv_neutralises_formula_like_cells(client, exp_db):
    token = make_client(exp_db, "ops", ["BLD-A"])
    exp_db.execute(text("INSERT INTO devices (device_id, building_id, name, period_seconds, power_threshold_kw) "
                        "VALUES ('-A1', 'BLD-A', 'meter', 60, 10)"))
    add_reading(exp_db, message_id="00000000-0000-4000-8000-00000000e003", device_id="-A1", metric="power_kw",
                event_time="2026-10-27T00:00:10Z", received_at="2026-10-27T00:00:11Z", value=1)
    exp_db.commit()
    job = post(client, token).json()["data"]
    rows = parse_csv(client.get(job["download_url"], headers=headers(token)).content)
    assert rows[1][1] == "'-A1"


def test_export_too_large_is_rejected_without_side_effect(database_url, tokens, exp_db, clock):
    app = create_app(Settings(database_url=database_url, export_max_rows=3), clock=clock)
    with TestClient(app) as c:
        r = post(c, tokens["ops"])
    app.state.engine.dispose()
    assert r.status_code == 422 and err(r) == "EXPORT_TOO_LARGE"
    assert count_exports(exp_db) == 0


def test_database_down_is_503_and_never_echoes_token():
    app = create_app(Settings(database_url="postgresql+psycopg://nobody@127.0.0.1:1/none"))
    with TestClient(app, raise_server_exceptions=False) as c:
        r = post(c, "tok-secret-value-0123456789")
    app.state.engine.dispose()
    assert r.status_code == 503 and err(r) == "DEPENDENCY_UNAVAILABLE"
    assert "tok-secret" not in r.text


def test_token_never_logged(client, tokens, caplog):
    caplog.set_level(logging.DEBUG)
    post(client, tokens["ops"])
    post(client, tokens["ops"], key="key-log-000002", building_id="BLD-B")
    # Đối chứng: đường ghi log audit thật sự đã chạy (nếu không, test pass rỗng như ở RED 2).
    assert "export created client=ops" in caplog.text and "export denied client=ops" in caplog.text
    assert tokens["ops"] not in caplog.text


def test_issued_token_is_stored_only_as_hash(exp_db):
    from app.export_clients import issue_client
    token = issue_client(exp_db, client_id="cli", name="CLI test", buildings=["BLD-A"], can_export=True)
    row = exp_db.execute(text("SELECT token_sha256 FROM export_clients WHERE client_id='cli'")).scalar()
    import hashlib
    assert row == hashlib.sha256(token.encode()).hexdigest() and token not in row
    dump = exp_db.execute(text("SELECT string_agg(t::text, '') FROM export_clients t")).scalar()
    assert token not in dump
