```markdown
# Yêu cầu & Quy tắc giả lập dữ liệu (Simulator Requirements) - Draft

**Mục đích:** Mô tả Simulator như một nguồn tạo dữ liệu và fixtures có thể tái lập để Backend và QA kiểm thử. 

## 1. Dữ liệu hợp lệ (Valid Fixtures)
*   Simulator cung cấp dữ liệu hợp lệ cho nhiều building và device tuân thủ nghiêm ngặt theo MQTT Schema sau khi được nhóm duyệt.

## 2. Fixtures dữ liệu đến trễ (Late Data)
*   **Mô tả:** Gửi bản tin ở thời điểm hiện tại nhưng gán giá trị `event_time` lùi về quá khứ. (Ví dụ: lùi 1 giờ chỉ để phục vụ mục đích tái lập kiểm thử, đây không phải là ngưỡng chính thức của hệ thống).
*   **Đề xuất xử lý:** Backend phân biệt được dữ liệu trễ dựa vào chênh lệch giữa `event_time` và `received_at`. Chính sách có kích hoạt cảnh báo hay không đối với dữ liệu trễ sẽ được thống nhất riêng.

## 3. Fixtures dữ liệu sai thứ tự (Out-of-order Data)
*   **Mô tả:** Bản tin được gửi không theo trình tự thời gian. Ví dụ: Gửi Bản tin A (`event_time` = 08:05:00Z), sau đó gửi Bản tin B (`event_time` = 08:00:00Z).
*   **Đề xuất xử lý:** Backend giữ lại cả hai reading. Khi truy vấn lịch sử, kết quả được sắp xếp đúng theo `event_time` (Không bắt buộc phải dùng Time-series DB cụ thể, miễn đáp ứng logic truy vấn này).

## 4. Fixtures trùng lặp dữ liệu (Duplicate Data)
*   **Mô tả:** Simulator gửi lại một payload có cùng `message_id` nhiều lần.
*   **Đề xuất xử lý:** Backend xử lý theo cơ chế idempotent (chỉ ghi nhận giá trị 1 lần, các lần gửi sau bị bỏ qua).

## 5. Fixtures không hợp lệ (Invalid Data)
*   **Mô tả:** Thiếu trường, sai kiểu, timestamp sai định dạng, ID không tồn tại.
*   **Kỳ vọng:** Backend phân biệt được bản tin bị từ chối với bản tin được chấp nhận.