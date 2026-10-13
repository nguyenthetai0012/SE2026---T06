# Yêu cầu & Quy tắc giả lập dữ liệu (Simulator Requirements)

**Mục đích:** Mô tả hành vi của Simulator, đặc biệt tập trung vào việc phát sinh các ca kiểm thử dữ liệu bất thường để Backend và QA đối chiếu.

## 1. Giả lập dữ liệu đến trễ (Late Data)
*   **Định nghĩa:** Bản tin có `event_time` (thời điểm đo) nhỏ hơn `received_at` (thời điểm server nhận) vượt quá một khoảng thời gian cho phép (ví dụ: trễ quá 5 phút).
*   **Cách Simulator giả lập:** Simulator vẫn gửi bản tin vào thời điểm hiện tại, nhưng chủ động gán giá trị `event_time` lùi lại 1 tiếng trước trong quá khứ.
*   **Kỳ vọng xử lý:** Backend vẫn tiếp nhận, nhưng đánh dấu là dữ liệu trễ và đưa vào báo cáo lịch sử thay vì kích hoạt cảnh báo thời gian thực.

## 2. Giả lập dữ liệu sai thứ tự (Out-of-order Data)
*   **Định nghĩa:** Bản tin được gửi/nhận không theo đúng trình tự thời gian thực tế xảy ra.
*   **Cách Simulator giả lập:** 
    *   Gửi Bản tin A: `event_time` = 08:05:00Z.
    *   Sau đó gửi Bản tin B: `event_time` = 08:00:00Z (Xảy ra trước A nhưng gửi sau).
*   **Kỳ vọng xử lý:** Cơ sở dữ liệu chuỗi thời gian (Time-series DB) phải sắp xếp lại đúng theo `event_time` để khi truy vấn lịch sử, đồ thị không bị gấp khúc sai lệch.

## 3. Trùng lặp dữ liệu (Duplicate Data)
*   **Cách Simulator giả lập:** Gửi đi gửi lại 2 bản tin có cùng giá trị `message_id`.
*   **Kỳ vọng xử lý:** Backend chỉ xử lý/lưu trữ bản tin đầu tiên và bỏ qua bản tin thứ hai.