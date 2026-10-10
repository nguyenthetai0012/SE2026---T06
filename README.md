# APP-05 Smart Campus Energy Dashboard

Dự án nhóm thuộc lĩnh vực **IoT / Realtime**, nhận dữ liệu cảm biến giả lập từ nhiều tòa nhà, cảnh báo tiêu thụ năng lượng bất thường và hiển thị lịch sử theo thời gian.

## Phạm vi đã xác nhận

Theo mô tả APP-05 trong tài liệu nhóm cung cấp:

- **MQTT ingestion:** tiếp nhận dữ liệu cảm biến qua MQTT.
- **Device registry:** quản lý danh mục thiết bị.
- **Dashboard:** hiển thị dữ liệu năng lượng của khuôn viên.
- **Alerts:** cảnh báo tiêu thụ năng lượng bất thường.
- **Time-series queries:** truy vấn dữ liệu lịch sử theo thời gian.
- **Offline device status:** theo dõi trạng thái thiết bị mất kết nối.

Các hạng mục kiểm chứng được đề tài nêu: **simulator, schema contract, load test và late/out-of-order data tests**.

## Trạng thái dự án

Dự án đang ở giai đoạn khởi tạo. Chưa có ứng dụng chạy được, contract được duyệt, pipeline CI hoặc kết quả kiểm thử chức năng và hiệu năng.

README này ghi nhận phạm vi theo nguồn được cung cấp. Các thiết kế chi tiết trong tài liệu vẫn cần nhóm xem xét và phê duyệt.

## Quyết định cần chốt trước khi triển khai

- Backend, frontend, cơ sở dữ liệu và MQTT broker.
- Metric, đơn vị đo, topic, payload và quy tắc validation.
- Chính sách dữ liệu trùng, đến muộn và sai thứ tự.
- Quy tắc phát hiện bất thường và ngưỡng cảnh báo.
- Chính sách xác định thiết bị offline.
- Cơ chế cập nhật dashboard, nhu cầu xác thực và môi trường triển khai.
- Kịch bản tải và tiêu chí nghiệm thu cụ thể.

MQTT, Node/Python, time-series DB và web UI được tài liệu liệt kê là công nghệ gợi ý. README không chốt framework, thư viện hoặc sản phẩm cụ thể.

Hai tài liệu có ví dụ payload và topic khác nhau; các ví dụ chưa được chọn làm contract chính thức.

## Cách làm việc

Quy trình đề xuất trong cẩm nang để nhóm duyệt:

1. Tạo Issue có nguồn yêu cầu, phạm vi, câu hỏi còn thiếu và tiêu chí kiểm chứng.
2. Chốt quyết định và contract liên quan trước khi coding.
3. Thực hiện trên nhánh riêng; chạy kiểm tra phù hợp với thay đổi.
4. Mở Pull Request có bằng chứng kiểm tra để thành viên khác review.
5. Merge và triển khai theo quy tắc nhóm đã thống nhất.

Trong Issue, tài liệu và PR, tách rõ **yêu cầu đã xác nhận**, **giả định** và **đề xuất cần duyệt**. Không tự đặt stack, schema, ngưỡng, deadline hoặc tiêu chí thiếu trong nguồn. Không commit secrets hoặc tuyên bố test pass khi chưa chạy.

## Cài đặt và chạy

Chưa có hướng dẫn chạy vì chưa có implementation và stack được duyệt. Các lệnh cài đặt, cấu hình, chạy simulator, chạy ứng dụng và kiểm thử sẽ được bổ sung sau khi kiểm chứng trong repo.

## Nguồn

Tài liệu do nhóm cung cấp:

- `APP05_KeHoach_TrienKhai_ChiTiet.docx`: mục 2.1 về đề tài; các phần thiết kế và backlog là đề xuất.
- `APP-05_Huong-dan-phoi-hop-ChatGPT-Codex-GitHub.docx`: bảng thông tin đề tài và cẩm nang cộng tác.

Các tài liệu nguồn chưa được đưa vào repo tại thời điểm soạn README.

