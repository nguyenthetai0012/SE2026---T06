# Backend API (bước 1B)

Khung Backend theo [baseline MVP](../../docs/decisions/mvp-baseline.md): FastAPI + Pydantic 2, SQLAlchemy 2 + psycopg 3, Alembic, PostgreSQL 16.
Phạm vi PR này: **schema DB, migration, seed registry, DTO/OpenAPI và các API đọc**. Chưa có worker ingestion MQTT, Docker Compose hay CI (bước 2B và 1D).
Contract: [`mvp-api.md`](../../docs/contracts/mvp-api.md); OpenAPI sinh từ code: [`mvp-openapi.json`](../../docs/contracts/mvp-openapi.json).

## Chạy

Cần Python 3.12 và PostgreSQL 16 có extension `btree_gist` (có sẵn trong gói contrib).

```bash
cd src/backend
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL='postgresql+psycopg://USER:PASSWORD@localhost:5432/energy'   # xem .env.example
alembic upgrade head                      # tạo schema (cần quyền CREATE EXTENSION cho lần đầu)
python -m app.seed                        # nạp registry từ seed/registry.json, chạy lại không nhân bản
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Biến môi trường: `DATABASE_URL` (bắt buộc, không có mặc định), `DB_STATEMENT_TIMEOUT_MS` (mặc định 8000, nhỏ hơn timeout 10 s của Frontend), `CORS_ORIGINS` (danh sách origin, cấm `*`). Không có secret nào trong Git.

## Kiểm thử

```bash
# TEST_DATABASE_URL phải trỏ tới database riêng, tên chứa "test": fixture sẽ DROP SCHEMA public.
export TEST_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@localhost:5432/energy_test'
cd src/backend && pytest                  # 67 test contract trên PostgreSQL thật, schema dựng bằng Alembic
python ../../tools/scripts/export_openapi.py --check   # file OpenAPI đã commit phải khớp app
```

Test dùng [`mvp-normal.json`](../../docs/testing/fixtures/mvp-normal.json) làm oracle (BLD-A 0.6 kWh, BLD-B 0.1 kWh, 2 alerts) và các biến thể trong ma trận [`mvp-acceptance.md`](../../docs/testing/mvp-acceptance.md): coverage partial, thiết bị disabled, null khác 0, biên `[start,end)` và `[start,end]`, biên offline/stale `>= 3*period`, phân trang, cursor không khớp, lỗi 404/422/503.
`tests/integration/backend/loader.py` chỉ nạp dữ liệu để kiểm đọc; **không phải worker ingestion**.

## Quyết định triển khai mà contract chưa nói (cần nhóm xác nhận)

1. `GET /health/ready` trả trong envelope `{"data":{"status":"ready"},"meta":{...}}` (bảng contract chỉ ghi `data`).
2. Building không có device enabled: `data_stale=false` (không có dữ liệu để coi là stale), `coverage=none`, `energy_kwh=null`.
3. `GET /buildings/summary` có `meta.next_cursor=null` và `meta.building_id` để giữ cùng hình dạng meta với các list khác.
4. Filter không áp dụng được echo là `null` trong `meta` (ví dụ `building_id: null`).
5. Cursor là opaque nhưng **không ký HMAC**: chỉ kiểm cấu trúc, kiểu và chữ ký truy vấn trước khi chạy SQL; không mang quyền.
6. Phương thức không phải GET trả 405 với mã lỗi `INVALID_QUERY` (contract chưa có mã riêng); đường dẫn lạ trả 404 `NOT_FOUND`.
7. `X-Request-ID` do client gửi chỉ được dùng lại nếu khớp `[A-Za-z0-9._-]{1,64}`; ngược lại sinh mới.

## Chưa làm / chưa kiểm chứng

- Worker ingestion (validation, idempotency, overlap ở tầng ứng dụng, alert sinh từ MQTT): bước 2B.
- Dockerfile, Compose, CI: bước 1D (Ngọc). Test mới chạy cục bộ, chưa chạy trên CI.
- Không có test tải; truy vấn chưa được đo trên dữ liệu lớn. Index theo thiết kế baseline, chưa có `EXPLAIN` trên dữ liệu thật.
