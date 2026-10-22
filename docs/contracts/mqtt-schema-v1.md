# MQTT Reading Schema — Draft Proposal v1

**Mục đích:** Đề xuất cấu trúc dữ liệu cảm biến (payload) được gửi từ Simulator qua MQTT Broker.

## 1. Các trường dữ liệu đề xuất

Các trường dưới đây là đề xuất ban đầu. Nhóm cần xác nhận trường nào bắt buộc, tập giá trị hợp lệ và quy tắc validation trước khi dùng schema làm contract được duyệt.

- `schema_version` (String): phiên bản schema (ví dụ: "1.0").
- `message_id` (String): mã định danh bản tin; đề xuất dùng để nhận diện bản tin trùng.
- `building_id` (String): mã tòa nhà (ví dụ: "BLD-A").
- `device_id` (String): mã thiết bị cảm biến (ví dụ: "METER-01").
- `event_time` (String): thời điểm cảm biến đo, định dạng ISO-8601 UTC.
- `metric` (String): loại thông số đo (ví dụ: "power_kw", "energy_kwh").
- `value` (Number): giá trị đo hữu hạn, không phải NaN hoặc vô cực.

`received_at` là thời điểm Backend nhận bản tin và do Backend ghi nhận; trường này không nằm trong payload Simulator.

## 2. Đề xuất ánh xạ metric sang đơn vị

Đây là đề xuất để Dashboard có ví dụ hiển thị; danh sách metric/đơn vị cần nhóm xác nhận.

- `power_kw` → `kW`
- `energy_kwh` → `kWh`

## 3. Ví dụ payload hợp lệ

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

## 4. Ví dụ payload không hợp lệ

Ví dụ này sai kiểu dữ liệu: `value` được gửi dưới dạng chuỗi, trong khi trường được đề xuất là một số hữu hạn. Ví dụ chỉ minh họa lỗi kiểu dữ liệu, chưa quyết định danh sách trường bắt buộc.

```json
{
  "schema_version": "1.0",
  "message_id": "msg-12346-invalid",
  "building_id": "BLD-A",
  "device_id": "METER-01",
  "event_time": "2026-10-13T08:01:00Z",
  "metric": "power_kw",
  "value": "45.5"
}
```

**Hành vi đề xuất:** Backend từ chối bản tin không hợp lệ và không đưa nó vào lịch sử như một reading hợp lệ. Cách phản hồi/lưu log chẩn đoán nội bộ cần được xác nhận theo thiết kế Backend.