# Ánh xạ API–Dashboard Frontend (Issue #21)

Trạng thái: đối chiếu triển khai Frontend với `docs/contracts/mvp-api.md` và OpenAPI trên `main`. Đây là bảng tích hợp phía Frontend; quyết định contract/API vẫn thuộc review chung Issue #21. Nguồn yêu cầu: `docs/requirements/dashboard.md`; view model/mock: `docs/requirements/frontend-view-model.md`.

## Ánh xạ màn hình và endpoint

| Luồng / tiêu chí | API nguồn | Dữ liệu → view model | Hành vi giao diện / phần mock thay bằng API |
| --- | --- | --- | --- |
| FLOW-01, AC-01 | GET /buildings/summary (start,end) | BuildingSummaryDto → BuildingSummary: building_id, name, energy_kwh, unit, start/end, coverage, coverage_ratio, included_interval_count, data_stale | Hiển thị một mục mỗi building; null giữ nghĩa chưa có dữ liệu, 0 giữ nghĩa 0; không tính lại aggregate ở UI. Thay nguồn mock summary bằng HttpDashboardRepository. |
| FLOW-02, AC-02, AC-05, AC-11 | GET /devices (building_id, limit, cursor) | DeviceDto → Device: device_id, building_id, name, status, last_seen, latest_event_time, data_stale, enabled | Lọc theo building từ API; render status nguồn trả về. Lỗi tải danh sách không đổi status thành offline. |
| FLOW-03/05, AC-03, AC-06, AC-10, AC-12 | GET /devices/{device_id}/readings (metric,start,end,limit,cursor) | ReadingDto → Reading: message_id, device_id, building_id, metric, event_time, received_at, interval_start, value, unit, is_late, is_out_of_order | Gửi đúng thiết bị/metric/range; hiển thị event_time, value/unit, received_at và cờ nguồn. Biểu đồ đặt X theo event_time trong range; bảng giữ thông tin thời gian. |
| FLOW-04, AC-04, AC-12 | GET /alerts (building_id,device_id,limit,cursor) | AlertDto → Alert: alert_id, message_id, device_id, building_id, event_time, detected_at, metric, value, threshold, unit, description | Chỉ render alert trả về; điều hướng dùng device_id/building_id khi có route tương ứng. Không tự phát hiện alert hoặc suy thêm severity/status. |
| Trạng thái tải / rỗng / lỗi, AC-07–09 | Phản hồi các endpoint; HTTP error envelope | ApiEnvelope / ApiErrorEnvelope → trạng thái repository/query | Loading trong lúc chờ; data=[] thành empty; lỗi thành error có retry giữ cùng query. Các trạng thái không bị gộp với offline. |

## Các tiêu chí xuyên màn hình

| Tiêu chí | Nguồn kiểm chứng |
| --- | --- |
| AC-01 đến AC-06 | Fixture mock hiện tại và API DTO; đối chiếu giá trị, đơn vị, phạm vi building/device và query. |
| AC-07 đến AC-09 | Unit/component tests của query states và retry cùng bộ lọc. |
| AC-10 | Chỉ gắn late/stale theo cờ do API trả; không suy đoán trên browser. |
| AC-11 | Tách lỗi tải dữ liệu khỏi Device.status. |
| AC-12 | Giữ building_id/device_id xuyên mapper và liên kết route; kiểm tra fixture nhiều building/device. |

## Giới hạn và phần mock cần thay

- Chế độ mặc định của ứng dụng vẫn dùng mock. Chuyển `VITE_DATA_MODE=api` để chọn HTTP repository; mapper giữ một ranh giới giữa wire DTO snake_case và view model camelCase.
- Lịch sử hiện tải một trang tối đa 100 readings và chưa có nút next-page; không tuyên bố đã hiển thị toàn bộ kết quả khi `next_cursor` khác null. Bổ sung paging UI là việc còn lại.
- Adapter hiện có API GET cho summary/devices/readings/alerts. `/health/ready` chưa được gọi trong UI.
- Không có endpoint ghi registry, acknowledge/resolve alert, realtime stream hoặc login trong phạm vi UI hiện tại.
- Thay mock chỉ sau khi cấu hình API mode; fixture vẫn được giữ cho unit/component tests.

## Cần xác nhận trong Issue #21

- Tài xác nhận request/response, metadata và lỗi ở phía Backend.
- An xác nhận ý nghĩa metric, thời gian đo/nhận và các cờ từ MQTT/Simulator.
- Ngọc xác nhận fixture/oracle và cách kiểm thử tích hợp.
- Sương xác nhận mapping màn hình/view model và hành vi mock/API nêu trong tài liệu này.

Các mục trên mô tả đối chiếu triển khai hiện tại; chúng không tự thay thế phê duyệt contract qua PR.