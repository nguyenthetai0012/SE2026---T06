# MQTT Schema Contract v1.0

**Mục đích:** Định nghĩa cấu trúc chuẩn cho dữ liệu cảm biến (payload) được gửi từ Simulator qua MQTT Broker.

## 1. Các trường dữ liệu (Fields)
*   `schema_version` (String): Phiên bản của schema (hiện tại là "1.0").
*   `message_id` (String): Mã định danh duy nhất của bản tin (dùng để chống trùng lặp dữ liệu/deduplication).
*   `building_id` (String): Mã định danh tòa nhà (VD: "BLD-A").
*   `device_id` (String): Mã định danh thiết bị cảm biến (VD: "METER-01").
*   `event_time` (String): Thời điểm đo thực tế tại cảm biến, định dạng ISO-8601 UTC.
*   `metric` (String): Loại thông số đo (VD: "power_kw", "energy_kwh").
*   `value` (Float): Giá trị đo lường.

## 2. Ví dụ Payload hợp lệ (Valid Payload)
```json
{
  "schema_version": "1.0",
  "message_id": "msg-12345-abcde",
  "building_id": "BLD-A",
  "device_id": "METER-01",
  "event_time": "2026-10-13T08:00:00Z",
  "metric": "power_kw",
  "value": 45.5
}
```
## 3. Ví dụ Payload KHÔNG hợp lệ (Invalid Payload)
* Thiếu trường bắt buộc: Không có message_id hoặc event_time.
* Sai kiểu dữ liệu (Type mismatch):
```json
{
  "schema_version": 1.0, 
  "building_id": "BLD-A",
  "device_id": "METER-01",
  "event_time": "13/10/2026", 
  "metric": "power_kw",
  "value": "bốn mươi lăm" 
}
```
*Lỗi thiếu trường hoặc sai kiểu sẽ bị Backend gạt bỏ hoặc ghi vào invalid*
