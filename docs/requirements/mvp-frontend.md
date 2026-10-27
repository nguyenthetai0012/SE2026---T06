# Frontend MVP và mock độc lập

Trạng thái: [baseline đề xuất](../decisions/mvp-baseline.md). Refs #4, #11, #12, #21.
Không thay FLOW01–05/AC01–12 trong [dashboard.md](dashboard.md).

## Màn hình và cách hoạt động

| Màn hình | API/DTO | Hành vi |
| --- | --- | --- |
| Tổng quan / | buildings/summary / BuildingSummary | Khoảng mặc định 24h được chụp một lần khi mở; đổi range mới đổi start/end. Card mỗi building, energy/unit/range, coverage và stale; click mở devices của building |
| Thiết bị /devices?building_id=... | devices / Device | Filter building, label online/offline/unknown/disabled, last_seen và dữ liệu cũ độc lập. Click device mở history |
| Lịch sử /devices/:id/history | readings / Reading | Chọn power hoặc energy, start/end; trục X event_time, tooltip value/unit/received_at/late; có bảng dữ liệu truy cập được |
| Cảnh báo /alerts | alerts / Alert | Filter building/device; mô tả, giá trị/ngưỡng, thời điểm đo và phát hiện; link thiết bị. Chỉ đọc |

UI tiếng Việt, giờ Asia/Ho_Chi_Minh, convert UTC lúc gửi API, ghi rõ timezone cạnh bộ lọc.
Range không hợp lệ chặn submit và hiện lỗi field; không xóa kết quả cũ rồi giả vờ không có dữ liệu.
Không có đăng nhập/CRUD registry/severity/ack trong MVP.
History chart dùng dữ liệu đã tải; khi next_cursor!=null ghi rõ chưa tải hết và nút tải thêm; không ngụy tạo đường liên tục qua khoảng thiếu dữ liệu.
Hiển thị energy=null là “Chưa có dữ liệu”, energy=0 là “0 kWh”; partial phải ghi “Điện năng ghi nhận — dữ liệu chưa đầy đủ”.
Offline là nhãn trạng thái thiết bị, không phải lỗi mạng.

## State và polling

Mỗi query key gồm endpoint + toàn bộ filters/range; chỉ response của key hiện tại được cập nhật UI.
Đổi filter hủy/ignore request cũ. Retry giữ nguyên key/start/end; không hứa cùng tập readings.
Initial loading có thông báo và không hiển thị empty sớm. 200 [] = empty + phạm vi; non-2xx/network/timeout = error + retry.
Refresh thất bại khi có dữ liệu cũ: giữ dữ liệu, hiện lỗi cập nhật và thời điểm lấy thành công, không đánh dấu dữ liệu mới.
Polling mỗi15s khi tab visible cho summary/devices/alerts trang đầu; không gọi chồng request; pause khi hidden/unmount.
History dùng nút refresh để không phá phân trang; refresh tải lại từ đầu.
Summary polling giữ range cố định; nút “24 giờ gần nhất” tạo range mới, không đổi range âm thầm.
Alerts refresh reset danh sách về trang đầu để tránh trộn cursor cũ.

## Thư mục và adapter

src/frontend/
- src/app/: routing/layout.
- src/features/{overview,devices,history,alerts}/: màn hình và UI state.
- src/api/: DTO, HTTP client, repository interface.
- src/mocks/: mock repository đúng DTO, fixture cases và clock cố định.
- src/components/: thành phần dùng chung.
- src/test/: unit/component tests.
- package.json, package-lock.json, vite.config.ts, tsconfig*.json.

Một interface có getSummary, getDevices, getReadings, getAlerts; tham số/return khớp [API](../contracts/mvp-api.md).
Mode mock/real bằng VITE_DATA_MODE; VITE_API_BASE_URL là public config, không chứa secret.
Mock giả lập response/error/delay trong repository, không rải if(mock) trong components.
Vitest/Testing Library test states, filters, retry và stale response; Playwright smoke bốn màn hình.
Chart thư viện cụ thể là lựa chọn scaffold, chưa ép thêm dependency; bảo đảm có bảng thay thế và nhãn đơn vị.

## Fixture cần triển khai

Dùng các ví dụ/quy tắc trong [nghiệm thu](../testing/mvp-acceptance.md) làm oracle, clock cố định.
Mỗi endpoint có success/empty/error/delayed; devices thêm offline/unknown; history thêm late/out-of-order; summary thêm partial/null/zero.
Không dùng chuỗi “power_kw (provisional example)” làm enum như mock draft; wire metric phải power_kw.
Kiểm tra mock DTO bằng typecheck; khi có Backend thêm contract tests so JSON thực với DTO.
Không cần chờ broker để code UI sau khi baseline được duyệt.

## Hoàn thành Frontend scaffold nghĩa là gì?

Đã commit lockfile/runtime version, chạy install sạch, lint, typecheck, test và build thật; lưu kết quả vào PR.
Không coi danh sách lệnh dự kiến trong tài liệu là bằng chứng đã chạy. Issue #11 chỉ đóng khi đạt các bước thực hiện được yêu cầu.
