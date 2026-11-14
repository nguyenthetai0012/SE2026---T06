# BT3 VT-023 — API xuất dữ liệu có phân quyền: cách chạy test

Bài cá nhân của Nguyễn Thế Tài (23001926), nhóm SE2026-T06. Baseline: `63ed1b9` (`main` ngày 2026-11-14).
**Đề xuất, chưa được nhóm duyệt.** Baseline MVP ghi "không có xác thực người dùng". Thay đổi này chỉ thêm xác thực bằng token máy cho `/api/v1/exports`; các API đọc khác giữ nguyên. Không merge khi nhóm chưa review.

## Có gì

| Thành phần | File |
| --- | --- |
| Migration: `export_clients`, `export_client_scopes`, `exports` (`UNIQUE(client_id, idempotency_key)`) | `src/backend/alembic/versions/0002_export_api.py` |
| Xác thực bearer token (DB chỉ lưu SHA-256) | `src/backend/app/auth.py`, `src/backend/app/export_clients.py` |
| Logic export + guard idempotency (`INSERT ... ON CONFLICT DO NOTHING`) | `src/backend/app/exports.py` |
| Route `POST /api/v1/exports`, `GET /api/v1/exports/{export_id}` | `src/backend/app/exports_api.py` |
| Test decision table, DB contract, unit (store giả) | `tests/integration/backend/test_export_api.py`, `test_export_schema.py`, `tests/unit/backend/test_export_service.py` |
| Thí nghiệm mutation (worktree tạm, không để lại mutant) | `tools/scripts/bt3_mutation.py`, `mutants/*.patch`, `results/mutation.json` |
| Tải 200 tác vụ đồng thời | `tests/load/export_load.py`, `results/load-*.json` |

## Chạy test (PostgreSQL 16 thật, có `btree_gist`)

```bash
cd src/backend
python3.12 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
# Database riêng, tên chứa "test": fixture sẽ DROP SCHEMA public
export TEST_DATABASE_URL='postgresql+psycopg://USER@localhost:5432/energy_test'
pytest -c pyproject.toml                       # toàn bộ: 129 test (76 cũ + 53 cho export)
pytest -c pyproject.toml ../../tests/unit/backend ../../tests/integration/backend/test_export_api.py \
       ../../tests/integration/backend/test_export_schema.py   # chỉ phần export
python ../../tools/scripts/export_openapi.py --check
```

Dùng `-c pyproject.toml` khi truyền đường dẫn test; thiếu cờ này pytest không đọc `pythonpath` và báo `No module named 'app'`.

Công cụ chỉ cài tạm để đo, **không** thêm vào `requirements-dev.txt` (theo AGENTS.md, phải được nhóm duyệt): `pip install pytest-cov==6.2.1 pytest-randomly==3.16.0`.

```bash
pytest -c pyproject.toml --cov=app --cov-branch --cov-report=term-missing   # coverage dòng + nhánh
pytest -c pyproject.toml -p randomly --randomly-seed=42                     # thứ tự ngẫu nhiên
TZ=Pacific/Kiritimati pytest -c pyproject.toml                               # múi giờ hệ thống khác
cd ../.. && python tools/scripts/bt3_mutation.py --repeat 10                 # 6 mutant, kết quả -> results/mutation.json
```

## Chạy tải

```bash
export DATABASE_URL='postgresql+psycopg://USER@localhost:5432/energy_load'   # tên chứa "load"
python tests/load/export_load.py prepare --tokens /tmp/bt3_tokens.json
(cd src/backend && uvicorn app.main:create_app --factory --port 8800 --workers 2) &
python tests/load/export_load.py run --tokens /tmp/bt3_tokens.json --out load-result.json
```

Kết quả đo (máy 2 vCPU, client và server chạy chung máy) nằm ở `results/`:
- Trước khi sửa (`before-fix/`): p95 khoảng 12 s, trượt mục tiêu.
- Sau khi đổi sang đọc cột bằng Core, đợt `a3fdb73/`: 1 worker cho p95 5,3–6,1 s (trượt); 2 worker cho p95 4,85–5,08 s (đạt 2/3 lần).
- Commit cuối `a2f06cf` (`load-w*-run*.json`): 1 worker cho p95 5,06–5,54 s (trượt 3/3); 2 worker cho p95 4,40–4,53 s (đạt 3/3).
- Giữa hai đợt đo có dao động khoảng 0,5 s, nên chưa coi là đạt vững.
- Mọi lần chạy: guard đúng (40 request cùng key chỉ tạo 1 export) và không rò dữ liệu.

## Cấp token cho client

```bash
cd src/backend && DATABASE_URL=... python -m app.export_clients --id ops --name "Ops script" --building BLD-A --can-export
```

Token chỉ được in ra một lần. Không commit, không dán token vào Issue hay log.
