# Kiến trúc MVP

Trạng thái và cấu hình: [baseline](../decisions/mvp-baseline.md). Refs #2, #20, #21.
Đây là thiết kế đề xuất hoàn chỉnh, không phải mô tả hệ thống đã chạy.

## Luồng dữ liệu

Simulator -> Mosquitto -> ingestion worker -> PostgreSQL -> HTTP API -> Dashboard.
Frontend không kết nối MQTT, không tính alert/offline hay cộng energy.
Worker và API là hai process riêng trong src/backend, dùng chung model và database; không khởi động consumer trong mỗi Uvicorn worker.
Một consumer MVP; registry/cấu hình được seed trước khi simulator chạy.

1. Simulator đọc registry seed, gửi reading theo topic của thiết bị.
2. Worker giới hạn kích thước, parse/validate schema, đối chiếu topic/registry.
3. Trong một transaction: kiểm tra idempotency và interval, lưu reading, cập nhật last_seen/latest_event_time, tạo alert nếu đủ điều kiện.
4. Chỉ acknowledge thành công sau commit. DB lỗi: không ACK, reconnect/retry; bản tin đã commit mà ACK thất lạc được dedup.
5. Invalid được loại và ACK để không lặp vô hạn; ghi mã lỗi và counter, không log nguyên payload/secrets.
6. API đọc DB, trả status/freshness theo server time, truy vấn thời gian/aggregate.
7. UI gọi HTTP, hiển thị loading/data/empty/error, polling và retry.

QoS1 không phải bảo đảm exactly-once đầu cuối. Simulator giữ message_id khi retry; worker dùng persistent MQTT client ID/session. Broker persistence + volume bật trong integration. Đo/reconcile số gửi/nhận ở load test để nhận diện mất dữ liệu, không cam kết zero-loss khi chưa đo.

## Model dữ liệu và bất biến

| Bảng | Dữ liệu / ràng buộc |
| --- | --- |
| buildings | building_id PK, name |
| devices | device_id PK toàn hệ thống, building_id FK, name, enabled, period_seconds>0, power_threshold_kw>=0, last_seen nullable, latest_event_time nullable |
| readings | message_id PK, device_id FK, metric, event_time timestamptz, received_at timestamptz, interval_start nullable, value numeric không âm; is_late, is_out_of_order; lưu period_seconds khi ingest |
| alerts | alert_id PK, message_id UNIQUE FK, device_id FK, event_time, detected_at, value_kw, threshold_kw, description |

Device thuộc một building cố định trong dataset MVP; không đổi mapping khi đã có readings.
Unique (device_id,metric,event_time); interval energy không được chồng lấn trong cùng device.
Dùng transaction + khóa device row cho kiểm tra overlap/high-watermark; unique constraint là lớp bảo vệ cuối cùng.
Index history (device_id,metric,event_time,message_id), alerts (detected_at,alert_id), devices(building_id).
Không lưu JSON float NaN/Infinity, không dùng giờ local trong DB; giữ độ chính xác decimal ở DB, API trả JSON number.

last_seen=max(received_at accepted); latest_event_time=max(event_time accepted).
is_out_of_order so với max event_time đã nhận của cùng device+metric trước transaction.
Online phụ thuộc last_seen, data_stale phụ thuộc latest_event_time: một reading cũ vừa đến có thể làm online=true nhưng data_stale=true. UI phải thể hiện được cả hai.

## Registry

MVP seed quản lý danh mục từ file cấu hình có validate, không phải tự đăng ký khi thấy topic lạ.
Tạo building trước device; seed chạy lại không nhân bản. Thay đổi dữ liệu cấu hình cần báo diff, không xóa lịch sử tự động.
Thiết bị unknown/disabled hoặc sai mapping bị reject, không cập nhật trạng thái.
Chưa có endpoint ghi registry hoặc màn hình quản trị; đây là giới hạn MVP rõ ràng.

## Phạm vi bảo mật và vận hành

Demo trên máy local: chỉ bind host ports vào 127.0.0.1, database không public; broker/API chỉ dùng trong môi trường tin cậy.
Secrets qua env, .env không commit; .env.example chỉ placeholder; browser chỉ được chứa API URL, không password DB/MQTT.
CORS allowlist đúng origin Frontend, không wildcard production. SQL parameterized; giới hạn payload và page size.
Không tuyên bố sẵn sàng public Internet: authentication, authorization, TLS, rate limiting và backup là điều kiện trước public deployment, không tự thêm vào phạm vi demo.
API /health/ready phản ánh DB; worker có health/counter riêng. Không báo worker khỏe chỉ vì API trả 200.
