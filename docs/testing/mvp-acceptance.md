# Nghiệm thu MVP và oracle dữ liệu

Trạng thái: [baseline đề xuất](../decisions/mvp-baseline.md). Bổ sung [test_plan.md](test_plan.md), không công bố test đã chạy.
Fixtures là dữ liệu mô phỏng; các giá trị không phải chuẩn hiệu năng/ngưỡng ngành điện.

## Fixture nền

Clock server 2026-10-27T00:03:00Z; 3 devices A-01/A-02 ở BLD-A và B-01 ở BLD-B; period60s, threshold10kW.
Query summary [00:00:00Z,00:02:00Z]. Mỗi device hai interval [00:00,00:01), [00:01,00:02).
A-01: power12, energy mỗi interval0.2; A-02: power6, energy0.1; B-01: power3, energy0.05.
message_id UUID duy nhất mỗi metric/device/time; received_at=event_time+1s.
Expected summary: BLD-A0.6kWh, BLD-B0.1kWh; coverage1; 4 interval A, 2 interval B; 2 alerts chỉ A-01 power.
Xóa một interval energy A-02 trong dataset fixture riêng: A=0.5, coverage0.75, partial. Không đọc power để bù thiếu.
Empty building dataset: energy=null, coverage none. Hai interval value0: energy=0, không null.
Mỗi test edge case dùng dataset riêng, reset rõ ràng để không trùng PK/overlap với fixture nền.

## Ma trận kiểm thử

| Case | Thiết lập | Expected | Trace |
| --- | --- | --- | --- |
| Valid ingest | Fixture nền | 12 readings, 2 alerts, 2 building totals đúng | TC01, AC01/12 |
| Duplicate | Phát lại nguyên reading vượt ngưỡng | Số reading/alert/last_seen không đổi | TC15 |
| Conflicting ID | Cùng ID đổi value | Reject MESSAGE_ID_CONFLICT; bản gốc giữ nguyên | TC15 |
| Invalid | Missing/type/bool/date/future/NaN/size/unknown/topic mismatch | Reject, không history/status/alert | TC02/03/04/17 |
| Overlap | Energy [00:00:30,00:01:30) sau [00:00,00:01) | Reject INTERVAL_OVERLAP | Energy correctness |
| Out of order | Gửi power00:03 rồi00:02, receive cùng00:03:01 | Lưu cả hai, order asc; cờ out_of_order cho00:02; không late vì age61s<=120 | TC13 |
| Late | Power event00:00 nhận01:00 | late=true; giữ event; alert nếu vượt10; latest không lùi | TC14, AC10 |
| Late boundary | age120s và120s+1us | false rồi true | Q8 |
| Offline boundary | last_seen00:00:00, now00:03:00 | offline; trước đó1us online | TC05, AC05/11 |
| Resume | Reading mới hợp lệ sau offline | online; duplicate/invalid không phục hồi | TC06 |
| Never seen | last_seen=null | unknown, stale=true | AC05 |
| Threshold | power9.9,10,10.1 ID khác | Chỉ10.1 tạo alert | TC07/08, AC04 |
| History boundary | power event=start, end-1us, end | Chỉ hai điểm đầu; đúng device/metric | TC09/10, AC03/06 |
| Summary boundary | Energy interval kết thúc=end | Được cộng nếu start interval>=query start | AC01 |
| Pagination | 3 readings, limit2 | Trang1=2,next!=null; trang2=1,next=null, không lặp | Q14 |
| Query errors | start>=end, invalid cursor, mismatch filters | 422 envelope; unknown ID404; DB down503 | TC10 |
| UI states | Pending, success, [], network error, retry | Loading/empty/error tách biệt, retry giữ filters | AC07/08/09 |
| UI races | Request A chậm, chuyển B | Response A không ghi đè B | AC12 |
| Offline vs lỗi | Lỗi network khi đang xem online | Error tải, không biến online thành offline | AC11 |
| Cross building | Chọn BLD-A | Chỉ devices/alerts A, link/history đúng | AC02/12 |
| Mock-real | Cùng DTO fixture và route | UI render cùng ý nghĩa | TC11/12 |
| Restart/DB failure | Worker dừng sau commit trước ACK; reconnect | Replay dedup, không thêm alert; báo trạng thái lỗi thật | Integration |

## Load không tự đặt SLA

Ngọc/An chạy profile nhỏ trước, tăng dần số devices/rate; các giá trị profile và máy chạy phải ghi trong báo cáo.
Ghi logical sent, accepted unique, duplicate, rejected theo mã, pending, failures; drain queue trước reconcile.
Đo throughput, p50/p95 latency ingest và API, tài nguyên DB/worker, tốc độ cập nhật UI.
Invariant bắt buộc: không trộn building/device; không double count; số accepted sau drain đối chiếu dữ liệu DB; sai lệch giải thích rõ, không báo PASS nếu không reconcile được.
Chưa có yêu cầu latency/throughput chính thức nên báo số đo, không tự đặt “đạt hiệu năng” hoặc hạn28ngày/291threads từ bài cá nhân.
TC16/18 phải có tham số và evidence thực; lỗi thiếu config phải fail rõ trước chạy.

## CI theo giai đoạn

Hiện chưa coi Gemini review là CI kiểm chứng.
Docs PR: check link nội bộ/JSON/format có thể chạy độc lập.
Scaffold: install lockfile, lint/typecheck, unit tests, build.
Integration: Postgres+MQTT service, seed fixture, contract/ingest tests.
E2E: web+API+worker, screenshot/report khi fail.
Load chạy manual với profile hữu hạn, không chạy stress mỗi PR.
Secrets không đưa vào log/artifact; GitHub token chỉ contents:read trừ job thực sự cần ghi.
Mỗi báo cáo ghi commit SHA, môi trường, lệnh, pass/fail và phần chưa chạy; việc sửa CI đang theo Issue #26.
