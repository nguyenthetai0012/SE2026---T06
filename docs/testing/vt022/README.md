# VT-022: harness giao dịch và thông báo

Đây là bài cá nhân có AI hỗ trợ, không phải worker MQTT hay tính năng đã được nhóm duyệt. Baseline: `63ed1b933d2f62a8753e91ee576606ce21c272fb`. Hàm `process_reading` tạo reading và alert với model của repo; sau commit mới gọi sender giả lập. Không có bảo đảm gửi lại sau crash, timeout sender, MQTT, idempotency hay một API ghi dữ liệu thực. `4096` là kích thước JSON hóa của dict trong harness, không phải kiểm chứng giới hạn byte của MQTT thật.

## Chạy kiểm tra

Cần Python >=3.12, PostgreSQL 16, quyền tạo extension `btree_gist` và database chuyên dụng có `test` trong tên. **Fixture của repo xóa schema public của database này.** Không trỏ vào database chứa dữ liệu cần giữ.

Từ `src/backend`, cài `requirements-dev.txt` và đặt biến môi trường `TEST_DATABASE_URL` tới database test riêng (không commit mật khẩu), sau đó:

```text
python -m pytest ../../tests/integration/backend/test_vt022_notification.py -v
python -m pytest -q -k "not test_db_down"
python ../../tests/load/vt022_burst.py
```

Lệnh tải cần seed A-01 sẵn trong database, ví dụ chạy test integration trước. Nó không xóa database và thêm 80 reading; chỉ chạy trên database thử nghiệm có thể bỏ đi. Kết quả không đo MQTT/HTTP hay gửi thông báo thật.

## Kết quả quan sát

Ngày 14/11/2026, Windows, Python 3.13.5, PostgreSQL 16.16: hai test đầu fail ở commit `e0f7a97` vì hàm khung báo `NotImplementedError`; không tuyên bố đó là failure của assertion nghiệp vụ. Sau patch `d5ac372`, 14 test VT-022 pass. Bộ liên quan backend: 89 passed, 1 deselected (`test_db_down` bị treo trong môi trường này), 1 cảnh báo deprecation. Coverage.py 7.17.3 cho module harness, gồm branch: 90% tổng hợp (55 statements, 4 missed; 16 branch, 3 partial). Không suy ra correctness từ tỷ lệ này.

Mutation tạm thời tại `app/queries.py`: thay mapping `value_kw` bằng `threshold_kw`; test API fail vì trả 10 thay 12. Code gốc được khôi phục sau thử nghiệm. Harness burst trên 80 thread, pool 20, sender no-op: 80 `sent`, p95 toàn bộ 0.5686 s; 80 input quá lớn đều `ValueError`, p95 0.0000652 s. Đây là hai burst cục bộ, không có mạng MQTT/API, không giả lập độ trễ sender; không đủ chứng minh SLA. Có lần chạy trước với p95 0.5267 s.

## Test cases và truy vết

| ID | Input / mục tiêu | Expected | Level / priority |
|---|---|---|---|
| T01 | Sender lỗi, AC3 | Reading + alert còn trong session mới | Integration / cao |
| T02 | Sender thành công, AC2 | Sender thấy alert đã commit | Integration / cao |
| T03 | 0 kW | Reading, không alert | Integration / vừa |
| T04 | 9.999 kW | Không alert | Integration / vừa |
| T05 | 10 kW tại ngưỡng | Không alert | Integration / cao |
| T06 | 10.001 kW | Alert và sender | Integration / cao |
| T07 | Giá trị âm | ValueError, không ghi | Integration / cao |
| T08 | Giá trị chuỗi | ValueError, không ghi | Integration / cao |
| T09 | Boolean | ValueError, không ghi | Integration / cao |
| T10 | NaN/Infinity | ValueError, không ghi | Integration / cao |
| T11 | Input quá 4096 byte theo harness | ValueError, không ghi | Integration / cao |
| T12 | Insert trùng lỗi, AC4 | Không gọi sender lần hai | Integration / cao |
| T13 | API đọc alert 12, threshold 10, AC5 | value=12, threshold=10 | API / cao |
| T14 | 80 event hợp lệ cùng lúc | Đo p95 và số lỗi | Load / cao |
| T15 | 80 input quá lớn cùng lúc | Đo rejection, p95 | Load / cao |

T01–T13 ở `tests/integration/backend/test_vt022_notification.py`; T14–T15 ở `tests/load/vt022_burst.py`. AC1 được T02/T06 kiểm; AC2 T02; AC3 T01; AC4 T12; AC5 T07–T13. Các test mở rộng được bổ sung sau patch và không phải toàn bộ evidence red trước patch. E2E thật chưa chạy vì chưa có worker MQTT được tích hợp.

Time/flaky: dùng timestamp cố định trong test; giá trị `received_at` dùng đồng hồ thật nên chưa khóa mọi trường hợp giờ. Isolation: fixture truncate bảng và test không an toàn khi chạy chung database song song; dùng database riêng. Concurrency/load phụ thuộc scheduler và pool nên cần lặp nhiều lần trước kết luận ổn định.

## AI usage và review

Codex được giao kiểm tra repo, lập kế hoạch và thực hiện test-first, mutation, tải và báo cáo theo yêu cầu người học. Prompt chính là yêu cầu VT-022 của người học trong cuộc hội thoại ngày 14/11/2026; kế hoạch được người học duyệt trước code. AI ban đầu giả định có thể dùng worker MQTT trên main: bác bỏ vì worker ở PR #41 chưa merge. AI cũng đề xuất database giả: sửa thành PostgreSQL thật do model dùng ràng buộc PostgreSQL. Người học vẫn cần tự đọc diff, test và reflection; không tuyên bố họ đã review từng dòng.

Hai điểm cần thách thức: test do AI sinh có thể chỉ assert lời gọi sender mà bỏ qua commit; T01/T02 dùng session mới. AI có thể khẳng định p95 của app từ burst cục bộ; kết luận đó bị bác bỏ vì test không đi qua MQTT/HTTP/sender thật. Không đặt secrets trong prompt hay repo.

Reflection 250–350 từ: **người học tự viết sau khi đọc code, chạy thử và ghi nhận điều mình thực sự làm**, bao gồm điều tăng confidence, điều chưa chứng minh và test tiếp theo.
