# MQTT Reading Schema — Draft Proposal v1

**Mục đích:** Định nghĩa cấu trúc chuẩn cho dữ liệu cảm biến (payload) được gửi từ Simulator qua MQTT Broker. 

## 1. Các trường dữ liệu (Fields)
*   `schema_version` (String): Phiên bản của schema (hiện tại là "1.0").
*   `message_id` (String): Mã định danh duy nhất của bản tin (dùng để chống trùng lặp dữ liệu/deduplication).
*   `building_id` (String): Mã định danh tòa nhà (VD: "BLD-A").
*   `device_id` (String): Mã định danh thiết bị cảm biến (VD: "METER-01").
*   `event_time` (String): Thời điểm đo thực tế tại cảm biến, định dạng ISO-8601 UTC. *(Lưu ý: Trường này khác với `received_at` - là thời điểm Backend tự ghi nhận khi nhận được bản tin, không nằm trong payload này).*
*   `metric` (String): Loại thông số đo (VD: "power_kw", "energy_kwh").
*   `value` (Float): Giá trị đo lường (là số hữu hạn).

## 2. Đề xuất quy tắc ánh xạ Đơn vị (Metric to Unit Mapping)
Để Dashboard có thể hiển thị chính xác theo yêu cầu, đề xuất quy tắc ánh xạ sau:
*   Nếu `metric` là `power_kw` -> Đơn vị hiển thị: `kW`
*   Nếu `metric` là `energy_kwh` -> Đơn vị hiển thị: `kWh`

## 3. Ví dụ Payload hợp lệ (Valid Payload)
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
## 4. Xử lý Payload KHÔNG hợp lệ (Invalid Payload)
Ca kiểm thử: Thiếu trường bắt buộc (không có message_id, event_time), sai kiểu dữ liệu, định dạng timestamp sai, hoặc định danh không có trong registry.

Đề xuất hành vi: Backend sẽ từ chối bản tin này và không cung cấp nó như một reading hợp lệ trong lịch sử (Cách phản hồi/lưu log chẩn đoán nội bộ sẽ do Backend quyết định).