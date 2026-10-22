# Dashboard Frontend View Model — Mock proposal

- Nguồn yêu cầu: [Issue #4](https://github.com/nguyenthetai0012/SE2026---T06/issues/4) và `docs/requirements/dashboard.md`.
- Issue thực hiện: [#12](https://github.com/nguyenthetai0012/SE2026---T06/issues/12).
- Trạng thái: **view model và fixture minh họa cho Frontend; chưa phải API, MQTT schema hay quyết định dữ liệu đã duyệt**.
- Fixture: [`fixtures/dashboard.mock.json`](fixtures/dashboard.mock.json).

## 1. Phạm vi

Tài liệu này chuyển các nhu cầu hiển thị đã ghi trong `dashboard.md` thành các nhóm dữ liệu UI cần dùng: tổng quan tòa nhà, thiết bị, readings theo thời gian và cảnh báo. Fixture dùng dữ liệu tổng hợp để thiết kế/kiểm tra trạng thái UI trước khi Backend API contract được thống nhất.

Tên trường và giá trị trong fixture chỉ là ví dụ view model nội bộ. Không dùng chúng làm API response, MQTT payload, công thức năng lượng, ngưỡng cảnh báo hoặc quy tắc offline.

## 2. Nhóm dữ liệu hiển thị

| Khu vực UI | Dữ liệu view model cần có | Giới hạn |
| --- | --- | --- |
| Tổng quan tòa nhà | Định danh/tên tòa nhà; giá trị năng lượng do nguồn cung cấp; đơn vị; khoảng thời gian áp dụng; dấu hiệu dữ liệu cũ nếu nguồn có | Frontend không tự cộng readings. Metric, đơn vị và khoảng mặc định trong fixture chỉ để minh họa. |
| Danh sách thiết bị | Định danh/tên thiết bị; building liên quan; trạng thái online/offline do nguồn cung cấp; last-seen nếu contract có | Không tự suy offline từ lỗi tải hoặc lịch sử rỗng. |
| Lịch sử cảm biến | Đối tượng đang chọn; metric; thời điểm đo; giá trị; đơn vị; khoảng truy vấn; thời điểm nhận hoặc nhãn late nếu nguồn cung cấp | Không tự đặt bộ lọc, múi giờ, biên khoảng hay ngưỡng late. |
| Cảnh báo | Định danh cảnh báo; liên kết tòa nhà/thiết bị; thời điểm và nội dung nguồn cung cấp | Fixture chỉ minh họa cảnh báo đã có; không mô tả thuật toán, threshold, severity hoặc thao tác xử lý đã được duyệt. |

### Thời gian và đơn vị trong fixture

Fixture dùng ISO-8601 UTC và các ví dụ `power_kw`/kW, `energy_kwh`/kWh để minh họa hình thức hiển thị. Chúng **không xác nhận contract**. README nói ví dụ trong tài liệu nguồn chưa được chọn làm contract; Issue #3 và #2 vẫn cần review/nhóm xác nhận trước tích hợp.

`event_time` trong fixture minh họa thời điểm đo; `received_at` minh họa thời điểm Backend nhận. Tên và ý nghĩa cuối cùng phải khớp contract được duyệt.

## 3. Trạng thái giao diện và truy vấn

Trạng thái truy vấn tách khỏi trạng thái thiết bị:

| Trạng thái truy vấn | Hành vi UI |
| --- | --- |
| Đang tải | Hiển thị trạng thái tải; chưa hiển thị kết quả rỗng. |
| Thành công có dữ liệu | Hiển thị dữ liệu đúng tòa nhà/thiết bị đang chọn. |
| Thành công rỗng | Hiển thị không có dữ liệu kèm điều kiện truy vấn; không báo lỗi. |
| Lỗi | Hiển thị lỗi và cho phép thử lại cùng đối tượng/điều kiện. |
| Thiết bị offline | Hiển thị riêng trạng thái do nguồn dữ liệu cung cấp; lỗi truy vấn không làm thiết bị thành offline. |
| Dữ liệu cũ/đến trễ | Chỉ gắn nhãn nếu nguồn/contract cung cấp trạng thái; không tự tính ngưỡng. |

Bảng trên là mô hình hành vi UI theo AC-07…AC-11, không quy định cách Backend mã hóa response hay cách Frontend triển khai state management.

## 4. Đối chiếu tiêu chí nghiệm thu Dashboard

| AC | Fixture/view model dùng để kiểm tra |
| --- | --- |
| AC-01 | Hai tòa nhà có ví dụ giá trị khác nhau, đơn vị và khoảng thời gian riêng; kiểm tra không tráo dữ liệu. |
| AC-02 | Thiết bị thuộc từ hai tòa nhà; lọc đúng phạm vi đang xem. |
| AC-03 | Nhiều readings của một thiết bị, có thời điểm/giá trị/đơn vị minh họa. |
| AC-04 | Một cảnh báo gắn đúng building và device. |
| AC-05 | Có thiết bị mock online và offline; UI hiển thị đúng trạng thái do fixture cung cấp. |
| AC-06 | Có nhiều thời điểm đo để kiểm tra phạm vi thời gian; quy tắc biên vẫn chờ contract. |
| AC-07 | Dùng kịch bản `loading` trong `queryScenarios`; đây là trạng thái UI mock, không phải API response. |
| AC-08 | Dùng kịch bản `success-empty` trong `queryScenarios` và hiển thị phạm vi truy vấn. |
| AC-09 | Dùng kịch bản `error-retry` trong `queryScenarios` và kiểm tra retry lặp lại cùng bộ lọc truy vấn. |
| AC-10 | Một reading được đánh dấu late trong mock để kiểm tra nhãn; không hàm ý ngưỡng chính thức. |
| AC-11 | Giữ offline status riêng với lỗi truy vấn và dữ liệu lịch sử rỗng. |
| AC-12 | Dùng ID liên kết xuyên suốt overview, devices, history và alert để kiểm tra không trộn đối tượng. |

## 5. Câu hỏi cần xác nhận trước tích hợp API

- Tài xác nhận dữ liệu Backend cho overview, registry, history, alerts và ba trạng thái kết quả truy vấn.
- An xác nhận nghĩa timestamp, danh sách metric/đơn vị, dữ liệu late/out-of-order và liên kết building/device.
- Ngọc xác nhận fixture có đủ để tạo test cho AC-01…AC-12 và các trường hợp rỗng/lỗi/offline.
- Nhóm chốt metric, đơn vị, khoảng mặc định, múi giờ/biên khoảng, ngưỡng freshness/late, quy tắc offline và trường cảnh báo trong các contract/decision tương ứng.

Khi API contract được duyệt, chuyển đổi API response sang view model tại ranh giới Frontend. Không để tên trường mock buộc Backend phải dùng cùng schema.
