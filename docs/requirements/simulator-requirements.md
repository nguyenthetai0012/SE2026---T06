# Yêu cầu và quy tắc giả lập dữ liệu (Simulator Requirements) — Draft

**Mục đích:** Mô tả Simulator như nguồn dữ liệu và fixtures có thể tái lập để Backend và QA kiểm thử.

## 1. Dữ liệu hợp lệ

Simulator cần tạo dữ liệu hợp lệ cho nhiều tòa nhà và thiết bị theo MQTT schema sau khi nhóm duyệt. Schema và metric cụ thể vẫn là đề xuất cho đến khi được xác nhận.

## 2. Dữ liệu đến trễ

- **Fixture:** Gửi bản tin ở thời điểm hiện tại nhưng đặt `event_time` lùi về quá khứ. Ví dụ lùi một giờ chỉ để tái lập kiểm thử, không phải ngưỡng chính thức.
- **Ý nghĩa:** `event_time` là lúc cảm biến đo; `received_at` là lúc Backend nhận và tự ghi nhận.
- **Chính sách:** Cách xử lý dữ liệu trễ, ngưỡng nhận diện và ảnh hưởng tới cảnh báo còn chờ nhóm thống nhất.

## 3. Dữ liệu sai thứ tự

- **Fixture:** Gửi bản tin A với `event_time` = 08:05:00Z, sau đó gửi bản tin B với `event_time` = 08:00:00Z.
- **Đề xuất:** Giữ cả hai reading; khi truy vấn lịch sử, sắp xếp theo `event_time`. Đây là yêu cầu hành vi đề xuất, không yêu cầu một loại cơ sở dữ liệu cụ thể.

## 4. Dữ liệu trùng lặp

- **Fixture:** Gửi lại payload có cùng `message_id`.
- **Đề xuất chờ xác nhận:** Backend xử lý idempotent để chỉ ghi nhận một lần. Tài/An cần xác nhận khóa nhận diện và hành vi cụ thể.

## 5. Dữ liệu không hợp lệ

Tạo fixtures cho các trường hợp thiếu trường, sai kiểu dữ liệu, timestamp sai định dạng và ID không có trong registry. Kết quả mong đợi là Backend phân biệt được bản tin bị từ chối với bản tin được chấp nhận; cách phản hồi chi tiết cần theo contract Backend đã duyệt.
