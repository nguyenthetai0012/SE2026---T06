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

Dự án đang chuẩn bị triển khai. Chưa có ứng dụng chạy được hoặc kết quả kiểm thử chức năng/hiệu năng. Các workflow hỗ trợ AI review không thay thế CI kiểm chứng ứng dụng.

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

## Phân công và kế hoạch ban đầu

> Tài liệu `APP05_PhanCong_Theo_CauTruc_Repo_KetHop_CapNhat.docx` đề xuất phân công dưới đây. Nhóm cần xác nhận trước khi xem đây là phân công chính thức:

| Thành viên | Vai trò đề xuất | Khu vực chính |
| --- | --- | --- |
| Tài — TV1 | Backend & API | `src/backend/`, API registry/history/alerts và API/contract tests |
| Sương — TV2 | Frontend & Dashboard | `src/frontend/`, dashboard, lịch sử, alerts/offline và E2E tests |
| An — TV3 | IoT, Simulator & Data | `src/simulator/`, MQTT/data flow, contract và dữ liệu trễ/sai thứ tự |
| Ngọc — TV4 | Quality, Security & DevOps | CI, test strategy, load/integration quality, scripts, Docker và release checklist |

Tài liệu cũng đưa ra kế hoạch 8 sprint một tuần làm mốc lập kế hoạch ban đầu. Đây là lịch đề xuất để nhóm điều chỉnh, không phải cam kết tiến độ:

1. **Foundation:** nền tảng repo và luồng chạy tối thiểu.
2. **MQTT path:** simulator, MQTT, ingestion và lưu readings.
3. **Registry & Queries:** quản lý thiết bị và truy vấn lịch sử.
4. **Dashboard MVP:** tổng quan, danh sách thiết bị và lịch sử.
5. **Alerts & Offline:** cảnh báo và trạng thái thiết bị.
6. **Reliability & Security:** dữ liệu trễ/sai thứ tự, bảo mật và khôi phục.
7. **Load & Release:** đo tải và chuẩn bị phát hành.
8. **Hardening & Demo:** ổn định, UAT, tài liệu và demo; desktop PoC là tùy chọn.

Các đầu việc chi tiết, tiêu chí tải, ngưỡng cảnh báo và quyết định kỹ thuật trong tài liệu cần được nhóm xác nhận qua Issue/PR trước khi triển khai.

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

- `APP05_PhanCong_Theo_CauTruc_Repo_KetHop_CapNhat.docx`: bản đồ trách nhiệm theo repo và kế hoạch 8 sprint đề xuất; nội dung đã được tóm tắt ở trên và cần nhóm xác nhận.
- `APP05_KeHoach_TrienKhai_ChiTiet.docx`: mục 2.1 về đề tài; các phần thiết kế và backlog là đề xuất.
- `APP-05_Huong-dan-phoi-hop-ChatGPT-Codex-GitHub.docx`: bảng thông tin đề tài và cẩm nang cộng tác.

Các tài liệu nguồn được cung cấp ngoài repo; README tách yêu cầu đã xác nhận khỏi phân công, lịch và thiết kế còn cần nhóm duyệt.


## Bộ tài liệu MVP tổng hợp — đề xuất duyệt chung

Bắt đầu từ [baseline MVP](docs/decisions/mvp-baseline.md), có stack, kiến trúc, MQTT, API, Frontend/mock, test oracle và thứ tự triển khai. Bộ này giải quyết cụ thể các câu hỏi mở bên trên, **đã được merge (PR #27) và được Tài, An xác nhận; Sương và Ngọc chưa xác nhận trên PR** nên phần của họ vẫn là đề xuất. Tài điều phối review/merge; sau khi chấp nhận, dùng bộ này làm cơ sở code thay các draft cũ.

[Dữ liệu nghiệm thu JSON](docs/testing/fixtures/mvp-normal.json) có 12 readings và kết quả kỳ vọng; đã kiểm tra phép tính fixture, chưa chạy qua Backend. [Hướng dẫn tích hợp](docs/tasks/mvp-implementation.md) ghi rõ các lệnh mục tiêu chưa được kiểm chứng trên ứng dụng.
