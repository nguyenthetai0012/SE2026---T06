# APP-05 — Baseline tài liệu MVP để bắt đầu triển khai

Trạng thái: **PROPOSED — bộ phương án hoàn chỉnh để duyệt chung**, ngày 2026-10-27.
Sương yêu cầu hoàn thiện tài liệu cả nhóm; điều này không thay thế xác nhận của Tài/An/Ngọc.
PR được merge sau review là mốc chấp nhận baseline; hiện chưa có bằng chứng nhóm duyệt các lựa chọn mới dưới đây.

## 1. Phạm vi và nguồn

Giữ phạm vi README và [Dashboard đã có trên main](../requirements/dashboard.md): ingest MQTT từ nhiều tòa nhà, registry, Dashboard, cảnh báo bất thường, lịch sử thời gian và offline. Giữ FLOW-01–05 và AC-01–12.
Không thêm bài cá nhân RE-022/R22/AD-022. Web trước; desktop là giai đoạn sau, chưa chọn Tauri/Electron.
MVP dùng dữ liệu mô phỏng, demo local; không đưa xác thực người dùng, CRUD registry trên UI, đóng cảnh báo, dự báo/ML vào MVP.

Nguồn kế thừa, không coi draft là đã duyệt:
- [PR #10](https://github.com/nguyenthetai0012/SE2026---T06/pull/10): schema và simulator.
- [PR #13](https://github.com/nguyenthetai0012/SE2026---T06/pull/13): hành vi Backend, kiến trúc, Q1–Q14.
- [PR #16](https://github.com/nguyenthetai0012/SE2026---T06/pull/16): view model/mock.
- [PR #17](https://github.com/nguyenthetai0012/SE2026---T06/pull/17): Frontend stack.
- [PR #23](https://github.com/nguyenthetai0012/SE2026---T06/pull/23): Backend/Simulator stack.
- [Test plan trên main](../testing/test_plan.md).

Bộ này tổng hợp và giải quyết các chỗ mở, không ghi đè lịch sử đóng góp. Sau khi duyệt, tài liệu mvp-* bên dưới là đặc tả kỹ thuật cho code; các PR draft trên cần đóng theo hướng đã được tổng hợp hoặc cập nhật liên kết, không merge lại những quyết định cũ mâu thuẫn.

## 2. Đề xuất stack thống nhất

| Thành phần | Lựa chọn | Lý do / giới hạn |
| --- | --- | --- |
| Frontend | React + TypeScript + Vite; npm, Node 22 >=22.12 | Theo hướng PR17; một web UI dùng lại API khi có desktop |
| Backend | Python 3.12, FastAPI, Pydantic 2, Uvicorn | Một ngôn ngữ với simulator; mô hình dữ liệu sinh OpenAPI |
| Storage | PostgreSQL 16; SQLAlchemy 2, psycopg 3, Alembic | Theo PR23; timestamptz và index cho time-series MVP; chưa cần extension |
| MQTT | Mosquitto 2, MQTT 3.1.1, QoS 1, Paho MQTT Python 2 | Giao nhận có thể lặp, ứng dụng idempotent |
| Simulator | Python 3.12 + Paho; seed tái lập | Không cần phần cứng |
| Tests | pytest; Vitest + Testing Library; Playwright | Unit/contract/integration/UI; load qua simulator |
| Chạy tích hợp | Docker Compose v2 | Các service nhất quán giữa máy và CI |

Không tuyên bố đây là stack tối ưu cho mọi quy mô. PostgreSQL đáp ứng truy vấn chuỗi thời gian ở MVP; benchmark sẽ quyết định có cần Timescale/Influx sau này.
Patch version của runtime, package và image phải được ghi/pin trong PR scaffold, kèm lockfile và bằng chứng build; tài liệu này không giả định đã cài hoặc chạy thành công.

Tài liệu chính thức tham khảo:
[Vite](https://vite.dev/guide/), [FastAPI](https://fastapi.tiangolo.com/features/),
[PostgreSQL timestamp](https://www.postgresql.org/docs/16/datatype-datetime.html),
[Paho](https://eclipse.dev/paho/clients/python/docs/), [Docker Compose](https://docs.docker.com/compose/).

## 3. Các quyết định giải quyết Q1–Q14

Các giá trị demo dưới đây là **đề xuất kỹ thuật mới**, không phải yêu cầu giảng viên hay ngưỡng ngành điện.

| ID | Phương án cụ thể |
| --- | --- |
| Q1 | energy_kwh là điện năng của một khoảng đo, có interval_start và event_time là cuối khoảng. Tổng quan cộng khoảng nằm trọn trong truy vấn; không lấy hiệu hai counter, không suy điện năng từ power_kw. Công thức và thiếu dữ liệu ở MQTT contract. |
| Q2 | UI mặc định 24 giờ gần nhất, gửi start/end rõ ràng. Lịch sử dùng [start,end). Tổng năng lượng tính các interval nằm trọn trong [start,end]; không chia tỷ lệ interval biên. |
| Q3 | Truyền/lưu UTC; UI Asia/Ho_Chi_Minh, ghi rõ múi giờ. |
| Q4 | building_id/device_id ổn định, phân biệt hoa thường; sensor là device_id + metric. |
| Q5 | Chu kỳ demo 60 giây; offline sau >=3 chu kỳ từ last_seen. Thiết bị chưa từng gửi là unknown, không gán online. |
| Q6 | last_seen là received_at lớn nhất của reading hợp lệ mới được chấp nhận; replay/invalid không refresh. |
| Q7 | event_time từ simulator; received_at chỉ Backend đặt tại lần nhận. |
| Q8 | is_late nếu received_at-event_time >2 chu kỳ. data_stale nếu latest_event_time chưa có hoặc now-latest_event_time >3 chu kỳ. Late và out-of-order độc lập. |
| Q9 | power_kw/kW và energy_kwh/kWh; value không âm, hữu hạn. |
| Q10 | Chỉ cảnh báo power_kw > ngưỡng cấu hình riêng thiết bị. Demo 10 kW. Mỗi reading vượt ngưỡng tạo một alert, duplicate không tạo lại. Không dùng ngưỡng tích lũy kWh. |
| Q11 | Alerts lọc building_id/device_id, có phân trang; chưa cần lọc thời gian. |
| Q12 | Alerts chỉ đọc, không severity hay trạng thái xử lý trong MVP. |
| Q13 | HTTP JSON: 200 có data hoặc data:[]; lỗi có error với code/message/request_id. |
| Q14 | History bắt buộc device, metric, start,end; limit/cursor, không cắt dữ liệu âm thầm. |

Cấu hình demo: period_seconds=60, offline_multiplier=3, late_multiplier=2,
freshness_multiplier=3, future_tolerance_seconds=5, alert_power_kw=10,
UI polling=15 giây, request timeout=10 giây, max_payload_bytes=4096,
API limit mặc định 100/tối đa 1000. Đây là cấu hình có thể đổi qua PR; không phải SLA.
Không tự động xóa lịch sử trong MVP; retention sản xuất ngoài phạm vi.
Đổi chu kỳ/threshold sau khi đã có dữ liệu cần một phiên dataset mới để không diễn giải lại dữ liệu cũ; mỗi reading/alert lưu thông số đánh giá tại thời điểm nhận.

## 4. Bộ tài liệu triển khai

1. [Kiến trúc, model và trách nhiệm](../architecture/mvp-system.md).
2. [MQTT, tính năng lượng và simulator](../contracts/mvp-mqtt.md).
3. [HTTP API và DTO](../contracts/mvp-api.md).
4. [Frontend và mock](../requirements/mvp-frontend.md).
5. [Nghiệm thu và fixtures](../testing/mvp-acceptance.md).
6. [Hướng dẫn tích hợp và thứ tự làm](../tasks/mvp-implementation.md).

Không cần đợi Backend chạy xong để làm UI: sau khi baseline được duyệt, Sương triển khai repository adapter + mock đúng DTO.
Không đánh đồng tài liệu hoàn chỉnh với chương trình đã kiểm thử.

## 5. Duyệt chung một lần

Tài điều phối review PR này; mỗi người rà đúng phần chuyên môn, không phải 4 người cùng bấm merge:
- Tài: stack, interval aggregate, API, model và lỗi.
- An: interval energy, topic, chu kỳ, late/out-of-order và fixture phát lại.
- Sương: dữ liệu đủ AC01–12, mock/real cùng DTO.
- Ngọc: test oracle, compose, secrets và báo cáo load.
Sau khi Tài ghi nhận thống nhất và merge, cập nhật trạng thái baseline thành Accepted và SHA phê duyệt. Không đánh dấu những ô trên đã được duyệt trước khi có bằng chứng.
