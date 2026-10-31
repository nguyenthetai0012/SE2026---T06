# HTTP API MVP v1

Trạng thái: [baseline đề xuất](../decisions/mvp-baseline.md). Refs #2, #21.
JSON UTF-8, base /api/v1. API đọc dữ liệu, không nhận ingest HTTP.

## Quy tắc chung

Timestamp UTC ISO8601 Z, ID theo MQTT. start/end bắt buộc cùng có, start<end; timestamp không timezone hoặc timezone khác Z: 422.
Query parameter không được liệt kê: 422; filter ID đúng format nhưng không tồn tại: 404.
device_id cùng building_id mà không cùng registry: 422 FILTER_MISMATCH.
metric không hỗ trợ: 422. start/end có thể trong quá khứ; không áp thời hạn 28 ngày hoặc SLA chưa được yêu cầu.
200 envelope: {"data":...,"meta":{"generated_at":"UTC timestamp",...}}.
Các list có meta.next_cursor (string opaque hoặc null); summary là list nhưng không phân trang vì MVP seed nhỏ.
Error: {"error":{"code":"INVALID_QUERY","message":"Thông báo an toàn","request_id":"trace-id"}}.
Mã: 422 INVALID_QUERY/FILTER_MISMATCH/INVALID_CURSOR; 404 NOT_FOUND; 503 DEPENDENCY_UNAVAILABLE; 500 INTERNAL_ERROR. Không trả stack trace/secret.
Không dùng 204 cho empty list. Backend chuẩn hóa lỗi validation FastAPI về envelope này.
Không cần login cho local demo, không dùng thiết kế này để public.

## Endpoints

| Method/path | Query | data | Sort |
| --- | --- | --- | --- |
| GET /buildings/summary | start,end bắt buộc; building_id optional | BuildingSummary[] | building_id asc |
| GET /devices | building_id optional; limit,cursor | Device[] | device_id asc |
| GET /devices/{device_id}/readings | metric,start,end bắt buộc; limit,cursor | Reading[] | event_time,message_id asc |
| GET /alerts | building_id,device_id optional; limit,cursor | Alert[] | detected_at,alert_id desc |
| GET /health/ready | không | {"status":"ready"} | 200 khi DB reachable; DB lỗi 503 |

Limit integer 1..1000, default100. Cursor encode last sort key và query signature, validate trước SQL; filter/range/limit đổi phải bỏ cursor. Không suy quyền từ cursor.
Mỗi page lấy limit+1 để đặt next_cursor khi còn dữ liệu. Không cắt kết quả rồi trả next_cursor=null.
Pagination là live view, không snapshot: late reading chèn trước cursor sẽ thấy khi tải lại từ trang đầu; UI giữ nguyên range, có nút refresh và không tuyên bố một lần phân trang là snapshot bất biến.
meta ở history luôn echo device_id,metric,start,end; summary echo start,end; các list echo filters áp dụng.
Request đang chạy quá 10 giây: frontend timeout/error/retry, không biến thành empty. Backend query timeout cần được scaffold cấu hình, không hứa SLA.

## DTO: mọi field dưới đây bắt buộc trừ khi ghi nullable

BuildingSummary:
- building_id:string, name:string.
- energy_kwh:number|null; unit:"kWh"; start/end:timestamp.
- included_interval_count:integer>=0.
- coverage:"complete"|"partial"|"none"; coverage_ratio:number 0..1.
- data_stale:boolean.
- Công thức và boundary theo [MQTT](mvp-mqtt.md); null không chuyển thành 0.

Device:
- device_id,building_id,name:string; enabled:boolean.
- status:"online"|"offline"|"unknown"|"disabled".
- last_seen:timestamp|null; latest_event_time:timestamp|null; data_stale:boolean.
- period_seconds:positive integer.
- disabled ưu tiên khi enabled=false; unknown khi last_seen=null; offline khi generated_at-last_seen >=3*period; còn lại online.
- data_stale=true nếu latest_event_time=null hoặc generated_at-latest_event_time >=3*period. Cùng biên với status=offline.
- Dùng cùng generated_at cho toàn page; UI không tự suy status từ thời gian máy khách.

Reading:
- message_id,device_id,building_id:string; metric:"power_kw"|"energy_kwh".
- event_time,received_at:timestamp; interval_start:timestamp|null (null cho power).
- value:number>=0; unit:"kW"|"kWh" tương ứng metric.
- is_late:boolean; is_out_of_order:boolean.
- Device disabled vẫn được truy vấn lịch sử; không có reading trả [].

Alert:
- alert_id,message_id,device_id,building_id:string.
- event_time:timestamp (reading), detected_at:timestamp (Backend tạo).
- metric:"power_kw"; value:number; threshold:number; unit:"kW"; description:string.
- value>threshold mới tạo, bằng ngưỡng không tạo; mỗi message_id tối đa một alert.
- Late reading vượt ngưỡng vẫn tạo alert lịch sử, giữ event_time cũ; UI không gọi đó là sự cố vừa xảy ra.
- Không severity, ack, resolved; tổng số alert có thể nhiều, luôn phân trang.

## Ví dụ phản hồi

GET /api/v1/devices?building_id=BLD-A:
```json
{"data":[{"device_id":"A-01","building_id":"BLD-A","name":"Meter A1","enabled":true,"status":"online","last_seen":"2026-10-27T00:01:01Z","latest_event_time":"2026-10-27T00:01:00Z","data_stale":false,"period_seconds":60}],"meta":{"generated_at":"2026-10-27T00:01:02Z","building_id":"BLD-A","next_cursor":null}}
```
Lỗi validation giữ một định dạng envelope nhất quán:
```json
{"error":{"code":"INVALID_QUERY","message":"start must be earlier than end","request_id":"req-mock-01"}}
```

Empty history giữ đúng query:
```json
{"data":[],"meta":{"generated_at":"2026-10-27T00:01:02Z","device_id":"A-01","metric":"power_kw","start":"2026-10-26T00:00:00Z","end":"2026-10-26T00:01:00Z","next_cursor":null}}
```

## OpenAPI và compatibility

PR Backend scaffold phải xuất OpenAPI từ model thực hiện, đối chiếu endpoint/DTO/error ở đây; không coi một OpenAPI chưa sinh là đã có.
Frontend định nghĩa DTO đúng bảng, adapter mapping tại một chỗ, không tự đổi snake_case trong wire format.
Breaking change phải sửa contract + fixture + adapter/tests trong cùng PR, tăng version khi đã có client sử dụng; không sửa âm thầm chỉ một phía.
