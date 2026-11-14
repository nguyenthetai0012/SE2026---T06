# VT-022: harness giao dịch và thông báo

Đây là bài cá nhân có AI hỗ trợ, không phải worker MQTT hay tính năng đã được nhóm duyệt. Baseline: `63ed1b933d2f62a8753e91ee576606ce21c272fb`. Hàm `process_reading` tạo reading và alert với model của repo; sau commit mới gọi sender giả lập. Không có bảo đảm gửi lại sau crash, timeout sender, MQTT, idempotency hay một API ghi dữ liệu thực. `4096` là kích thước JSON hóa của dict trong harness, không phải kiểm chứng giới hạn byte của MQTT thật.

## Chạy kiểm tra

Cần Python >=3.12, PostgreSQL 16, quyền tạo extension `btree_gist` và database chuyên dụng có `test` trong tên. **Fixture của repo xóa schema public của database này.** Không trỏ vào database chứa dữ liệu cần giữ.

Từ `src/backend`, cài `requirements-dev.txt` và đặt biến môi trường `TEST_DATABASE_URL` tới database test riêng (không commit mật khẩu), sau đó:

```text
python -m pytest ../../tests/integration/backend/test_vt022_notification.py -v
python -m pytest -q -k "not test_db_down"
python ../../tests/load/vt022_burst.py
python ../../tests/load/vt022_size_probe.py
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

## Bổ sung sau review bài cá nhân

Sau patch, thêm test ở commit `5b4944ec48b90d3cb44225f240529b3c9a0b6c4b`:

- Nhóm unit kiểm tra cổng kích thước JSON chính xác 4095, 4096, 4097, 65536 và 1048576 byte. Để điều chỉnh kích thước, test đệm chuỗi `device_id`; các giá trị dài này **không phải định danh thiết bị hợp lệ**. Hai giá trị đầu chỉ chứng minh đã đi qua kiểm tra size tới điểm mở database giả, không chứng minh event được chấp nhận hay ghi thành công.
- Test failure-path bơm lỗi vào `before_commit`; session mới kiểm tra không có reading/alert và sender chưa được gọi. Hai test đóng băng đồng hồ với sai lệch 60 và 121 giây, kiểm tra cờ `is_late` và invariant khi sender lỗi. Có thêm test thiếu trường, timestamp không timezone và thiết bị không tồn tại.
- Kết quả: 27 test VT-022 pass; bộ backend 102 pass, 1 deselected (`test_db_down` từng treo), 1 warning. Chạy đảo thứ tự và thứ tự xáo trộn seed 22: mỗi lượt 27 pass. Các kiểm tra này giảm rủi ro phụ thuộc thứ tự, chưa loại trừ mọi dạng flaky. Có lần test ban đầu bị lỗi kết nối PostgreSQL do giới hạn môi trường (9 pass/18 error), sau đó chạy lại trong môi trường có quyền kết nối. Lệnh chạy đảo đầu tiên cũng sai đường dẫn và không thu test, đã sửa trước lượt thành công.
- Coverage mới cho riêng module harness: 54/55 dòng (98,18%), 16/16 nhánh do coverage.py nhận diện (100%); tổng hợp làm tròn 99%. Thiếu dòng 45 ở đường chuyển exception. Không suy ra mọi tổ hợp điều kiện, lỗi đồng thời hoặc chất lượng toàn hệ thống đã được bao phủ.
- Ba burst hợp lệ với PostgreSQL, 80 thread, pool 20, sender no-op có p95 lần lượt 0,5506; 0,5128; 0,5812 giây. `vt022_size_probe.py` đo 3 lượt mỗi kích thước, 80 tác vụ/lượt: 4097 byte p95 0,000041–0,000087 giây; 65536 byte 0,000345–0,000457 giây; 1048576 byte 0,006990–0,007643 giây. 720/720 bị từ chối đúng lý do size; thời gian cả burst 1 MiB 0,505–0,553 giây. Đây là input cố ý không hợp lệ, dùng chung đối tượng bất biến mỗi burst; đồng hồ của từng tác vụ bắt đầu sau barrier, không gồm tạo input/chờ barrier. Không có MQTT, HTTP, mạng hay sender thật; không thể kết luận SLA sản phẩm hoặc mọi mức input.
- `process_reading` tuần tự hóa toàn bộ input **trước** khi kiểm tra giới hạn; chi phí CPU/bộ nhớ vẫn tăng theo kích thước. Cần giới hạn bytes ở lớp nhận dữ liệu thật trước parse và đánh giá memory/timeout. Ngưỡng 4096 là giả định cho harness, không phải contract đã được nhóm phê duyệt.

Mutation riêng: commit [`24201a95e51f987caed16e3ad53d7a3b210341b7`](https://github.com/nguyenthetai0012/SE2026---T06/commit/24201a95e51f987caed16e3ad53d7a3b210341b7) trên nhánh `experiment/vt-022-response-mutation` **chứa lỗi cố ý, không merge**. Thay đổi một dòng `value_kw` thành `threshold_kw`; bản nội dung tương ứng được thử cục bộ, test `test_alert_api_maps_value_and_threshold` thất bại `10.0 == 12`. Đã khôi phục cục bộ, đối chiếu nội dung `queries.py` với nhánh nộp bài là giống nhau; chưa chạy lại test database sau lần mutation bổ sung này vì lượt duyệt quyền không hoàn tất. Trước mutation, cùng test nằm trong lượt 27 pass. Lần mutation ban đầu cũng có lượt chạy lại test sau khôi phục. Nhánh nộp bài không chứa mutation.

Các lệnh thêm, chạy từ `src/backend` sau khi cài thêm `coverage` trong môi trường test:

```text
python -m coverage run --branch --source=app.vt022_notification -m pytest ../../tests/integration/backend/test_vt022_notification.py -v
python -m coverage report -m
python ../../tests/load/vt022_size_probe.py
```

Lệnh mutation có thể tái lập bằng worktree/checkout tách biệt tại commit mutation trên và chạy `python -m pytest ../../tests/integration/backend/test_vt022_notification.py::test_alert_api_maps_value_and_threshold -v`; kỳ vọng test FAIL, sau đó quay về nhánh nộp bài. Fixture xóa schema nên phải dùng database test riêng. Không lưu log thực thi hay mật khẩu vào repository theo AGENTS.md.
