# Công việc tuần 1–3 — Nguyễn Thị Hồng Ngọc

Ngày ghi nhận: **05/11/2026**, theo múi giờ Asia/Ho_Chi_Minh. Vai trò: Quality, Security & DevOps.

## 1. Căn cứ và phạm vi

Đối chiếu phần Ngọc — TV4 trong tài liệu nguồn `APP05_PhanCong_Theo_CauTruc_Repo_KetHop_CapNhat.docx` do nhóm cung cấp ngoài repo:

| Tuần | Phân công nguồn | Phần đã triển khai | Phần còn phụ thuộc |
| --- | --- | --- | --- |
| 1 | CI, Docker/dev scripts, Issue/PR templates, checklist branch, kiểm tra khởi chạy sạch | Workflow QA; PostgreSQL/MQTT; script init/config/up/smoke/down; hai mẫu Issue, một mẫu PR và checklist branch | Workflow chưa chạy trên GitHub; quản trị viên chưa bật branch protection; chưa có full-stack demo trong checkout này |
| 2 | Contract tests, replay/duplicate, đưa checks vào CI | Contract fixture checks có thể chạy ngay; suite MQTT thật đã viết và từ chối chạy thiếu worker | Chưa có worker nên chưa chứng minh ingestion/replay/duplicate đến DB |
| 3 | Migration, API integration, event-time, chỉ mục/query behavior | Chạy Backend thật từ snapshot riêng; bổ sung 7 bài kiểm tra migration/seed/index/query/API | Backend snapshot chưa được nhập vào nhánh hiện tại; cần chạy lại trên commit tích hợp cuối |

Phần QA dùng stack đã được đề xuất trong [baseline](../decisions/mvp-baseline.md), không tự thay đổi contract hay ghi baseline thành Accepted. Kết quả trên snapshot không thay thế review/merge của nhóm. Không đưa code Backend, worker hay simulator mới vào `src/` trong thay đổi này.

## 2. Tuần 1 — Môi trường và quy trình

Các file chính:

- [Compose PostgreSQL/MQTT](../../infrastructure/docker/compose.yml), [cấu hình broker](../../infrastructure/docker/mosquitto.conf).
- [Script môi trường dev](../../tools/scripts/dev.py), [.env.example](../../.env.example).
- [Workflow QA](../../.github/workflows/qa.yml).
- [Mẫu công việc](../../.github/ISSUE_TEMPLATE/task.md), [mẫu báo lỗi](../../.github/ISSUE_TEMPLATE/bug.md), [mẫu PR](../../.github/PULL_REQUEST_TEMPLATE.md).
- [Checklist branch](ngoc-branch-checklist.md).

Chạy từ thư mục gốc repo, cần Python 3 và Docker Desktop/Compose v2 đang hoạt động:

```bash
python3 tools/scripts/dev.py init
python3 tools/scripts/dev.py config
python3 tools/scripts/dev.py up
python3 tools/scripts/dev.py smoke
python3 tools/scripts/dev.py status
```

`init` tạo `.env` bằng mật khẩu ngẫu nhiên, không in mật khẩu và không ghi đè file đang có. Không commit `.env`. `config` chỉ xác nhận cấu hình hợp lệ, không in nội dung đã nội suy secrets.

Project Docker là `app05-ngoc-qa`; database dev là `app05_qa`, không publish cổng DB ra host. MQTT chỉ publish `127.0.0.1:1883`. Nếu cổng bận, đổi `MQTT_PORT` trong `.env` rồi chạy lại. Container ứng dụng tương lai dùng hostname `db`/`mqtt` trong mạng Compose này. Broker hiện cho anonymous trong môi trường local tin cậy; chưa dùng cho public deployment.

Healthcheck DB dùng `pg_isready`; broker dùng publish QoS 1. Smoke thực hiện `SELECT 1` và publish/subscribe một topic QA ngẫu nhiên, rồi xóa retained probe. Topic này nằm ngoài `campus/v1/.../readings` và không giả làm dữ liệu ingestion.

Dừng môi trường, giữ lại volumes:

```bash
python3 tools/scripts/dev.py down
```

Không dùng `down -v` theo mặc định. Đây là hướng dẫn hạ tầng QA, chưa phải hướng dẫn chạy toàn bộ ứng dụng.

## 3. Tuần 2 — Contract và replay

### Kiểm tra fixture chạy ngay

```bash
python3 tools/scripts/check_repo.py
python3 -m unittest discover -s tests/integration -p 'test_contract_*.py' -v
```

[Bộ kiểm tra fixture](../../tests/integration/test_contract_fixtures.py) dùng [oracle QA](../../tests/integration/qa_contract.py) độc lập với Backend để kiểm tra JSON/schema đề xuất: trường bắt buộc, kiểu giá trị, timestamp UTC, topic/registry, interval, JSON key trùng, kích thước payload và các biên liên quan.

Fixture nền được đối chiếu bằng Decimal: 12 readings duy nhất, 2 alerts kỳ vọng, BLD-A 0.6 kWh, BLD-B 0.1 kWh và coverage 1. Đây là xác minh dữ liệu kiểm thử, **không phải bằng chứng worker xử lý được 12 readings**. Oracle này không được import vào mã nguồn sản phẩm làm validator thay cho Backend.

### Kiểm thử MQTT thật đã chuẩn bị

[Suite MQTT](../../tests/integration/test_live_mqtt.py) có 5 tình huống: power hợp lệ, replay duplicate, duplicate với JSON đổi thứ tự key, xung đột message ID và value sai kiểu. Suite publish thật qua broker rồi kiểm tra DB thật; không có fake consumer hoặc loader thay worker.

Trước khi chạy, Tài/An cần cung cấp worker thật, migration và seed trong DB `app05_qa`, kết nối đúng broker của project QA. A-01 phải enabled, thuộc BLD-A, period 60 giây, threshold 10 kW. Chỉ sau khi xác minh worker đã chạy mới dùng:

```bash
QA_MQTT_WORKER_READY=1 python3 -m unittest discover -s tests/integration -p 'test_live_mqtt.py' -v
```

Suite ghi dữ liệu tổng hợp UUID mới vào DB QA. Mỗi ca replay dùng bản tin hợp lệ làm mốc xác nhận consumer đã xử lý đến đoạn cần kiểm tra, dựa trên một worker MVP xử lý tuần tự cùng topic. Cửa sổ đợi 15 giây là timeout của bài kiểm tra, không phải SLA. Nếu triển khai worker xử lý song song thì cần điều chỉnh cơ chế xác nhận trước khi dùng suite này làm gate.

Chưa bao phủ đầy đủ mọi lỗi ingestion hoặc chứng minh duplicate không refresh `last_seen`: cần mở rộng kiểm tra theo worker thực tế và counter/điểm đồng bộ của nó. Thiếu worker/schema phải báo BLOCKED/lỗi với exit khác 0; không skip để tạo kết quả xanh.

## 4. Tuần 3 — Migration, API và query

### Chạy trên Backend trong checkout hiện tại

```bash
python3 tools/scripts/backend_qa.py
```

Lệnh kiểm tra mã nguồn cần thiết trước khi chạy Docker. Nếu Backend chưa tồn tại, trả exit 2 kèm danh sách file thiếu. Không tạo Backend giả để vượt qua preflight.

### Chạy trên snapshot nhánh Backend

Lần kiểm chứng này dùng nhánh đã có trong local remote refs:

```text
origin/feature/issue-21-backend-read-api-scaffold
SHA: c2b3953dd70f7821c61a85cb50faf49b078fe45e
```

Tạo lại snapshot từ đúng SHA (không checkout hoặc merge đè nhánh đang làm):

```bash
mkdir -p /private/tmp/app05-ngoc-backend-snapshot
git archive c2b3953dd70f7821c61a85cb50faf49b078fe45e src/backend tests/integration/backend docs/testing/fixtures/mvp-normal.json docs/contracts/mvp-openapi.json tools/scripts/export_openapi.py | tar -x -C /private/tmp/app05-ngoc-backend-snapshot
python3 tools/scripts/backend_qa.py --source-root /private/tmp/app05-ngoc-backend-snapshot
```

Trên Linux/CI có thể thay đường dẫn snapshot bằng thư mục tạm phù hợp. Nếu SHA chưa có trong clone, cần lấy nhánh Backend tương ứng rồi đối chiếu SHA trước khi chạy.

[Compose Backend QA](../../infrastructure/docker/compose.backend-qa.yml) tạo service `db-test`, database `app05_test` riêng bằng tmpfs, không có host port. Tests được phép dựng lại schema trong DB test này; không chạy chúng vào database có dữ liệu cần giữ. Script dừng và xóa container DB test khi xong; không xóa volumes DB dev.

Container mount source chỉ đọc, sao chép các phần cần thiết vào `/work`, cài đúng requirements của nhánh Backend rồi chạy 67 tests có sẵn và [7 tests bổ sung của Ngọc](../../tests/integration/qa_backend/test_ngoc_week3.py):

1. Migration downgrade về base, upgrade về head, chạy upgrade lại và kiểm revision.
2. Seed chạy lại không nhân registry và không làm mất readings.
3. Chỉ mục devices, readings và alerts đúng các cột thiết kế.
4. History SQL lọc/sắp xếp đúng; lưu `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`.
5. History rỗng giữ đúng envelope và điều kiện truy vấn.
6. Nạp dữ liệu theo thứ tự đảo, API vẫn trả event-time tăng dần, phân trang không lặp.
7. Query parameter không hỗ trợ trả lỗi 422 đúng envelope.

API được gọi qua FastAPI TestClient với PostgreSQL thật. Đây là integration tại tầng API/DB; chưa kiểm tra HTTP qua reverse proxy hay luồng MQTT ingestion. Các readings trong tests đọc được nạp bằng loader của nhánh Backend, không được tính là thành công của worker.

Bằng chứng sinh vào `build/qa/` (được gitignore): JUnit XML, query plan, môi trường và danh sách dependency đã resolve. Không commit output build/log. File báo cáo này lưu kết luận và điều kiện để tái lập; số đo query trên fixture nhỏ không phải benchmark tải.

## 5. Kết quả đã chạy

Môi trường kiểm chứng: macOS host, Docker Engine 28.1.1, Compose v2.36.0-desktop.1, container Linux ARM64. Script offline chạy với Python 3.14.7 trên host; Backend chạy Python 3.12.12, pytest 9.2.0 trong container. Image pin patch: `postgres:16.15-alpine`, `eclipse-mosquitto:2.0.22`, `python:3.12.12-slim`.

Nền repo của nhánh QA: `08a0f4e`; thay đổi QA hiện là working tree trên `feature/issue-26-ngoc-weekly-readme`. Backend dùng SHA đầy đủ ở trên. Số lượng test bao gồm phần có sẵn của Backend, không phải tất cả đều do Ngọc viết mới.

| Kiểm tra | Kết quả thực tế | Giới hạn |
| --- | --- | --- |
| `dev.py config` | PASS | Kiểm cú pháp/cấu hình Compose, không chứng minh app chạy |
| `dev.py up` từ volumes mới | PASS; DB/MQTT healthy | Chỉ hạ tầng QA |
| `dev.py smoke` | PASS; DB SELECT và MQTT publish/subscribe | Chưa có worker/API trong stack dev |
| `check_repo.py` | PASS | JSON, link nội bộ, Python syntax, diff và `.env` không tracked |
| Contract fixture suite | 9 tests PASS | Oracle/fixture, chưa qua Backend ingestion |
| Backend snapshot + tests Ngọc | 74 tests PASS; 0 failure/error/skip | 67 có sẵn + 7 bổ sung; snapshot chưa merge |
| Backend preflight tại checkout hiện tại | BLOCKED, exit 2 đúng dự kiến | Chưa có `src/backend` thực thi |
| MQTT suite khi chưa xác nhận worker | BLOCKED, exit khác 0 đúng dự kiến | Chưa chạy 5 test nghiệp vụ MQTT |
| GitHub Actions | CHƯA CHẠY trên GitHub | Workflow mới được tạo cục bộ |

Backend phát một cảnh báo deprecation của Starlette khi dùng httpx TestClient; đã ghi nhận, không tự đổi dependency thuộc Backend trong task này. EXPLAIN lần kiểm chứng có `Index Scan` qua `ix_readings_history`, trả 2 rows; không đặt hoặc kết luận đạt SLA từ số đo đó.

## 6. CI và điều kiện bàn giao

Workflow hiện có hai job tự động cho PR/push main: kiểm tài liệu/fixture và smoke PostgreSQL/MQTT. Job Backend chạy qua workflow_dispatch với `backend_ready=true` sau khi Backend có trong checkout được chọn; nếu bật khi thiếu mã nguồn sẽ fail rõ. Job này lưu `build/qa/` thành artifact 7 ngày.

Sau khi Backend/worker được tích hợp, cần đưa integration vào required checks theo quy tắc nhóm; không dùng hai job fixture/infra thay bằng chứng full-stack. Chỉ nhóm/quản trị viên có quyền mới bật branch protection và chốt required checks trên GitHub.

Các việc còn cần bàn giao:

- Tài: đưa Backend/migration/seed được duyệt vào nhánh tích hợp; cung cấp worker và cách chạy.
- An: simulator phát hữu hạn, replay cùng ID và dữ liệu lỗi theo contract đã duyệt.
- Ngọc: chạy lại suite MQTT thật, kiểm bổ sung `last_seen`, lưu counter/kết quả reject; chạy CI trên GitHub.
- Reviewer/nhóm trưởng: review diff, xác nhận phần baseline liên quan và merge theo quy trình.

Phát hiện fixture/mock để Sương/Tài rà soát riêng: mock UI có reading trễ 130 giây nhưng `is_late=false`, và summary BLD-A có `data_stale=false` dù device enabled A-02 stale. Không sửa contract hoặc dữ liệu giao diện ngoài phạm vi QA này.

Tham khảo triển khai: [Docker Compose services](https://docs.docker.com/reference/compose-file/services/), [Mosquitto configuration](https://mosquitto.org/man/mosquitto-conf-5.html), [GitHub Actions workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).
