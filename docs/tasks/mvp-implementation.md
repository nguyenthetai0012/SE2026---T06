# Hướng dẫn triển khai và chạy tích hợp MVP

Trạng thái: thiết kế theo [baseline](../decisions/mvp-baseline.md); **chưa phải runbook đã chạy thành công**. Refs #11, #12, #20, #21, #22, #26.

## Thứ tự ngắn nhất

| Bước | Người chính | Phần làm | Điều kiện hoàn tất |
| --- | --- | --- | --- |
| 0 | Tài + An/Sương/Ngọc review phần mình | Duyệt baseline một lần, xử lý phản biện cụ thể trong PR | PR có quyết định và merge bởi Tài |
| 1A | Sương | Scaffold React/TS/Vite, adapter/mock và layout | Install sạch/lint/typecheck/test/build chạy thật; #11/#12 |
| 1B | Tài | Backend scaffold, migration/seed, DTO/OpenAPI và read APIs | Contract tests với DB fixture, không phụ thuộc simulator |
| 1C | An | Simulator + fixture modes | Payload đúng contract, deterministic seed, finite load |
| 1D | Ngọc | Compose services, CI scaffold, test fixtures | Reproducible config, secrets placeholders; #22/#26 |
| 2A | Sương | Bốn màn hình và states qua mock | AC01–12 component tests |
| 2B | Tài + An | Worker ingestion/dedup/alerts/status/summary | Integration edge cases theo test matrix |
| 3 | Cả nhóm, Ngọc điều phối | Chuyển UI real mode, E2E/load, chạy từ checkout sạch | Evidence và sửa lỗi; hoàn thiện runbook #22 |

Không chờ hoàn thành #22 (cần hệ thống thật) mới bắt đầu 1A–1D. Tài liệu không thay thế implementation acceptance của các Issue.
Một Issue/PR cho một thay đổi có thể review; không tạo nhánh mới mỗi lần agent sửa cùng task.
Các draft PR10/13/16/17/23 đã đóng góp đầu vào; sau khi baseline được duyệt, ghi link tổng hợp và xử lý trạng thái để không còn hai bản đặc tả cạnh tranh. PR18 quy tắc AGENTS vẫn review riêng.

## Giao diện chạy cần được scaffold thực hiện

Tên dưới đây là giao diện vận hành đề xuất, chưa tồn tại trong repo.
Compose file infrastructure/docker/compose.yml; services db, mqtt, migrate, seed, api, worker, frontend, simulator.
db/mqtt có persistent volumes; api/worker chỉ start sau migrate thành công; seed là job chạy rõ ràng; simulator không tự phát vô hạn khi compose up.
Host ports localhost: frontend5173, api8000; MQTT1883 chỉ publish local nếu cần simulator ngoài container; DB không cần publish mặc định.
Healthcheck db và broker; API ready kiểm DB; worker health cần xác nhận connected/subscribed và DB writable.

Env example cần có:
DATABASE_URL, MQTT_HOST, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD,
MQTT_CLIENT_ID, CORS_ORIGINS, VITE_API_BASE_URL, VITE_DATA_MODE,
SIM_SEED, SIM_DURATION_SECONDS; demo policy lấy từ baseline/registry seed.
Giá trị secret là placeholder; không có token/credential thực trong Git. Biến VITE_* public.
Tên host trong container là service db/mqtt/api, không dùng localhost cho liên lạc giữa container.

## Các lệnh mục tiêu (CHƯA XÁC MINH)

Scaffold phải tạo các service/scripts này rồi Ngọc thử và sửa runbook theo thực tế:
```text
docker compose -f infrastructure/docker/compose.yml config
docker compose -f infrastructure/docker/compose.yml up -d db mqtt
docker compose -f infrastructure/docker/compose.yml run --rm migrate
docker compose -f infrastructure/docker/compose.yml run --rm seed
docker compose -f infrastructure/docker/compose.yml up -d api worker frontend
docker compose -f infrastructure/docker/compose.yml run --rm simulator
docker compose -f infrastructure/docker/compose.yml logs api worker simulator
docker compose -f infrastructure/docker/compose.yml down
```
down giữ volume; không hướng dẫn down -v mặc định vì mất dữ liệu.
Frontend standalone mock: cd src/frontend; npm ci; npm run dev.
Các scripts mục tiêu lint/typecheck/test/build phải được thêm vào package.json trước khi coi lệnh hợp lệ.
Python requirements lock/venv và lệnh pytest phải được scaffold ghi rõ; không coi dependency list là lockfile.

## Smoke và troubleshooting

1. Fresh checkout, tạo .env từ example; xác nhận config không thiếu mà không in secret.
2. Migrate+seed; /api/v1/health/ready trả200.
3. Worker subscribed; chạy simulator finite; DB nhận readings và alert vượt ngưỡng.
4. Mở UI, kiểm hai building/history, offline A-02 và phục hồi; đối chiếu totals fixture.
5. DB lỗi -> API503; broker lỗi -> worker báo unhealthy; UI không tự gán offline do HTTP lỗi.
6. Dừng/khởi động lại, kiểm persistence và duplicate không nhân bản.
Nếu không có readings: kiểm topic/registry/credentials/worker errors, không sửa schema để “cho qua”.
Nếu CORS lỗi: kiểm origin và API URL; không mở wildcard theo thói quen.
Nếu frontend chỉ thấy mock: kiểm VITE_DATA_MODE và build env, không tuyên bố tích hợp thành công.

## Bằng chứng cần bổ sung khi có code

Ngọc ghi OS/runtime/image versions, commit SHA, env names (không values secret), command/output cần thiết, URL local, pass/fail và hạn chế.
#22 chưa thể đóng chỉ bằng tài liệu này; cần chạy tích hợp thật. #11 cần build thật. #21 cần đối chiếu OpenAPI khi Backend sinh model.
Sau PR tài liệu, code bắt đầu theo baseline đã duyệt, không tiếp tục mở thêm vòng tài liệu cho các lựa chọn đã chốt.
