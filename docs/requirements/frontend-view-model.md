# Frontend view model và mock cho Issue #12

Trạng thái: **mock nội bộ cho Frontend**. Không phải quyết định API/MQTT đã duyệt.
Nguồn: [Issue #12](https://github.com/nguyenthetai0012/SE2026---T06/issues/12), [yêu cầu Dashboard](dashboard.md), và các DTO trong [PR #27](https://github.com/nguyenthetai0012/SE2026---T06/pull/27).

## Trạng thái nguồn và các giả định cô lập

`docs/decisions/mvp-baseline.md` cùng các DTO `mvp-api.md` trên PR #27 vẫn ở trạng thái **PROPOSED**; PR đang mở không phải bằng chứng cả nhóm đã duyệt contract. Comment review của Tài đồng ý riêng với React/TypeScript/Vite, nhưng PR #27 vẫn đang chờ review/xác nhận các phần khác. Vì vậy:

- Frontend dùng các DTO snake_case của PR #27 làm **wire shape tạm thời** trong `src/api/dto.ts`.
- `src/api/mapper.ts` là nơi duy nhất đổi wire DTO sang view model camelCase cho giao diện.
- `src/api/repository.ts` là nơi duy nhất chọn mock hay API; API endpoint và query mapping nằm trong `src/api/httpRepository.ts`.
- Mock nằm trong `src/mocks/`; component không rẽ nhánh theo chế độ mock/API.
- Bất kỳ thay đổi DTO sau khi PR #27 được duyệt chỉ cần sửa adapter/mapping và fixture tương ứng; giao diện phụ thuộc view model.

## Dữ liệu theo màn hình

| Màn hình | View model hiển thị | Nguồn DTO đề xuất | Quy tắc Frontend |
| --- | --- | --- | --- |
| Tổng quan | Building ID/tên, `energyKwh` nullable, unit, khoảng thời gian, số interval, coverage/ratio, cờ stale | `BuildingSummary` | Hiển thị `null` là chưa có dữ liệu, `0` là 0 kWh; không tự cộng hay tính coverage. Partial được ghi rõ là dữ liệu chưa đầy đủ. |
| Thiết bị | Device ID, building ID, tên, status, last seen, stale | `Device` | Hiển thị `online`/`offline`/`unknown`/`disabled` theo nguồn; stale là thông tin riêng. Lỗi tải danh sách không làm thiết bị thành offline. |
| Lịch sử | Message/device/building ID, metric, event/received time, interval, value/unit, late/out-of-order | `Reading` | Lọc theo device/metric/range; giữ cờ do nguồn trả về; hiển thị bảng cùng biểu đồ đơn giản. Không suy cờ từ timestamp phía browser. |
| Cảnh báo | Alert/message/device/building ID, event/detected time, metric, value/threshold/unit, description | `Alert` | Chỉ hiển thị alert do repository trả về; không tự tạo alert, severity, trạng thái xử lý hay ngưỡng. |

Các tên field, route, metric, status và envelope ở cột DTO lấy từ đề xuất PR #27, chưa phải API contract được nhóm chấp thuận. Nhãn và ngữ nghĩa chỉ được thay khi nhóm duyệt contract.

## Mock scenarios

Fixture được type-check tại `src/mocks/fixtures.ts` bằng chính các DTO đề xuất. Dữ liệu là synthetic và có clock cố định:

- Hai building với coverage partial/complete và giá trị riêng; repository có scenario `zero` và `null-energy` để UI phân biệt 0 với null.
- Thiết bị online, offline, unknown và disabled; trạng thái được hiển thị theo field nguồn, không được tính lại.
- History có `received_at`, late và out-of-order; kết quả mẫu được trả theo thứ tự event time của DTO.
- Alert mẫu liên kết đúng device/building; mock không chạy quy tắc threshold.
- Scenario `delayed`, `empty`, `error-once` và `error-refresh` kiểm tra loading, empty thành công, error/retry và lỗi refresh khi vẫn giữ dữ liệu cũ.

Scenario được chọn trong mock repository hoặc qua query parameter chỉ ở development. Chúng không thay đổi HTTP/MQTT contract và không giả làm dữ liệu thật.

## Đối chiếu AC-01…AC-12

| AC | Bằng chứng Frontend |
| --- | --- |
| AC-01 | Overview render riêng hai building ID và giá trị/range/unit từ DTO. |
| AC-02 | Bộ lọc building gọi repository theo phạm vi và giữ liên hệ device/building. |
| AC-03 | History chọn device/metric/range; bảng và biểu đồ dùng đúng readings được trả về. |
| AC-04 | Alert render thông tin và link về đúng device lịch sử. |
| AC-05 | Nhãn offline gắn trên đúng thiết bị; fixture có cả online/offline. |
| AC-06 | Mock repository lọc readings theo device/metric và khoảng `[start,end)` của DTO đề xuất. |
| AC-07 | Scenario delayed cho thấy loading trước response. |
| AC-08 | Scenario empty trả success rỗng, không hiện error. |
| AC-09 | Scenario error-once cho phép retry cùng filter/range. |
| AC-10 | History giữ timestamp và late flag do DTO cung cấp, không trình bày dữ liệu trễ như mới. |
| AC-11 | Error state riêng với status offline/unknown của Device. |
| AC-12 | Filter và links giữ đúng building/device identity giữa summary, devices, history, alerts; test kiểm tra chuyển từ summary sang danh sách lọc. |

Issue #12 còn chờ nhóm duyệt view model và DTO nguồn. PR này không sửa API/MQTT contract, không định nghĩa công thức năng lượng, alert threshold hay freshness/offline policy.
