# Ranh giới dữ liệu và API Backend — bản nháp Issue #2

**Chưa được duyệt; không phải schema hoặc API contract thực thi.** Nguồn, giới hạn đối chiếu Word, chức năng và tiêu chí nghiệm thu: [backend-api-requirements.md](../architecture/backend-api-requirements.md).

## Thông tin đầu vào cần thống nhất với An (#3)

| Nhóm thông tin ở mức khái niệm | Mục đích | Quyết định còn thiếu |
| --- | --- | --- |
| Định danh thiết bị và tòa nhà | Liên kết registry, lọc lịch sử | Kiểu/tên trường; cách kiểm tra quan hệ; xử lý thiết bị chưa đăng ký |
| Thời điểm đo | Đặt điểm đo trên chuỗi thời gian | Định dạng, múi giờ, độ chính xác, sai lệch đồng hồ, biên timestamp hợp lệ |
| Metric, giá trị, đơn vị | Diễn giải phép đo | Danh mục metric, kiểu số, miền giá trị và phép đổi đơn vị; phân biệt công suất với năng lượng |
| Nhận diện sự kiện nếu cần | Xử lý giao lại/trùng | Cách nhận diện, phạm vi duy nhất và thời hạn đối chiếu |
| Topic và metadata giao nhận | Xác định nguồn/phiên bản | Cấu trúc topic, kiểm tra topic với payload, schema version, QoS/retain và quyền publish |
| Thời điểm Backend nhận | Tính độ trễ và tín hiệu sống | Quy tắc ghi nhận; phân biệt với thời điểm đo; không yêu cầu Simulator tự cung cấp mốc này |

Các dòng là nhu cầu thông tin, không ấn định trường JSON. Payload mẫu và schema do #3 đề xuất; chưa chọn một trong các ví dụ khác nhau mà README nhắc tới.

Trước khi khóa contract, cần fixture cho: hợp lệ; thiếu/sai định danh; timestamp không hợp lệ; metric/đơn vị không hỗ trợ; trùng; đến trễ; sai thứ tự; thời điểm ở tương lai. Mỗi fixture phải có kết quả chấp nhận/từ chối/xử lý được Tài và An thống nhất.

## API ở mức yêu cầu để rà soát với Sương (#4)

Chưa quy định HTTP method/path, schema response, mã lỗi cụ thể, cơ chế realtime hoặc xác thực.

| Năng lực | Đầu vào khái niệm | Đầu ra tối thiểu đề xuất | Nhánh lỗi/trạng thái cần thể hiện |
| --- | --- | --- | --- |
| Danh sách/chi tiết thiết bị | Phạm vi tòa nhà, định danh, bộ lọc trạng thái nếu duyệt | Định danh, quan hệ tòa nhà, thông tin hiển thị; trạng thái kết nối và mốc cập nhật | Danh sách rỗng, thiết bị không tồn tại, lỗi tải, trạng thái chưa xác định |
| Đăng ký/cập nhật thiết bị nếu duyệt | Định danh và thông tin registry được phép thay đổi | Kết quả thao tác và bản ghi sau cập nhật | Định danh trùng, tòa nhà không hợp lệ, dữ liệu sai, quyền không đủ nếu có xác thực |
| Lịch sử | Phạm vi, metric, khoảng thời gian; mức tổng hợp nếu duyệt | Điểm đo theo thời điểm đo, giá trị, đơn vị; metadata về thứ tự/giới hạn/độ mới | Bộ lọc sai, metric không hỗ trợ, rỗng, kết quả bị giới hạn, lỗi truy vấn |
| Tổng quan năng lượng | Phạm vi khuôn viên/tòa nhà và khoảng thời gian | Các giá trị theo công thức đã duyệt, đơn vị, phạm vi, độ mới và mức đầy đủ | Thiếu dữ liệu, không thể tính, rỗng, lỗi; không mặc định thiếu dữ liệu là 0 |
| Cảnh báo | Phạm vi, thời gian; lọc loại/trạng thái nếu duyệt | Định danh để tham chiếu, thiết bị/tòa nhà, thời điểm, giá trị/đơn vị và lý do | Không có cảnh báo, bộ lọc sai, lỗi; vòng đời cảnh báo chưa chốt |
| Offline | Phạm vi hoặc định danh | Trạng thái, lần liên lạc gần nhất nếu có, thời điểm đánh giá | Chưa có tín hiệu, offline, phục hồi, lỗi; trạng thái kết nối không thay thế trạng thái tải API |

Dashboard phải nhận đủ ngữ cảnh để không nhầm dữ liệu đo cũ, thiết bị offline và lỗi tải API. Quy tắc tổng hợp, biên thời gian, timezone hiển thị, sắp xếp/phân trang và cập nhật realtime cần thống nhất trước khi viết API contract cụ thể.

## Bảng câu hỏi cần nhóm trả lời

| ID | Câu hỏi/quyết định | Người cần phối hợp | Nơi theo dõi | Trạng thái |
| --- | --- | --- | --- | --- |
| D-01 | Schema, topic, metric/đơn vị, timestamp và validation nào được chọn? | An và Tài | [#3](https://github.com/nguyenthetai0012/SE2026---T06/issues/3) | Chưa xác nhận |
| D-02 | Xử lý thiết bị lạ, dữ liệu trùng, trễ/sai thứ tự và timestamp tương lai thế nào? Có ảnh hưởng cảnh báo/tổng quan đã tính không? | An, Tài, Ngọc | #3 và [#5](https://github.com/nguyenthetai0012/SE2026---T06/issues/5) | Chưa xác nhận |
| D-03 | Registry có những thao tác nào; ai được sửa; thay đổi/xóa thiết bị hoặc tòa nhà ảnh hưởng lịch sử ra sao? | Tài và nhóm | [#2](https://github.com/nguyenthetai0012/SE2026---T06/issues/2) | Chưa xác nhận |
| D-04 | Dashboard dùng metric/công thức nào; cần raw hay aggregate; dữ liệu thiếu và độ mới biểu diễn thế nào? | Sương và Tài | [#4](https://github.com/nguyenthetai0012/SE2026---T06/issues/4) | Chưa xác nhận |
| D-05 | Khoảng thời gian bao gồm biên nào; timezone, thứ tự, giới hạn/phân trang và lỗi API ra sao? | Sương, Tài, Ngọc | #2, #4, #5 | Chưa xác nhận |
| D-06 | Quy tắc bất thường, ngưỡng, chống lặp và vòng đời cảnh báo nào được duyệt? | Tài và nhóm | #2 | Chưa xác nhận |
| D-07 | Tín hiệu sống là gì; timeout/biên timeout; trạng thái trước tín hiệu đầu và khi phục hồi? Bản tin lỗi, trễ hoặc replay có tính là tín hiệu sống không? | An, Tài, Sương | #2, #3, #4 | Chưa xác nhận |
| D-08 | Cơ chế cập nhật Dashboard, nhu cầu xác thực/phân quyền và truy cập MQTT? | Tài, Sương, Ngọc | #2, #4, #5 | Chưa xác nhận |
| D-09 | Kịch bản tải và chỉ tiêu nghiệm thu cụ thể? | Ngọc, An, Tài | #5 | Chưa xác nhận |
| D-10 | Backend/frontend, lưu trữ và broker nào được chọn sau khi yêu cầu rõ? | Cả nhóm | Quyết định sau review, ghi vào docs/decisions/ | Chưa xác nhận |

## Ghi nhận phối hợp và review

Chưa có bằng chứng thống nhất hoặc review của thành viên khác tại thời điểm soạn. Khi có phản hồi, cập nhật bảng dưới với liên kết comment/review/PR thật; không đánh dấu duyệt chỉ vì tài liệu đã được commit.

| Nội dung | Kết quả | Bằng chứng |
| --- | --- | --- |
| Đối chiếu Word nguồn | Chưa thực hiện: môi trường chưa đọc được file | Chưa có |
| Đầu vào MQTT với An | Chờ rà soát D-01, D-02, D-07 | Issue #3, chưa có phản hồi xác nhận |
| Dữ liệu Dashboard với Sương | Chờ rà soát D-04, D-05, D-07, D-08 | Issue #4, chưa có phản hồi xác nhận |
| Kiểm chứng với Ngọc | Chờ rà soát tiêu chí BE-01…BE-06 và D-09 | Issue #5, chưa có phản hồi xác nhận |
| Review thành viên khác | Chưa có | Bổ sung liên kết review PR sau khi thực hiện |

Sau khi duyệt: ghi kết luận và bằng chứng, cập nhật các tài liệu liên quan, rồi mới mô tả contract cụ thể và triển khai. Các mục chưa thống nhất vẫn giữ trạng thái mở.
