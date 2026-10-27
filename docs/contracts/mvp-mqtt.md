# MQTT và Simulator MVP

Trạng thái: [baseline đề xuất](../decisions/mvp-baseline.md). Refs #3, #20.
Kế thừa PR10 và bổ sung quy tắc còn thiếu. Nếu được duyệt, dùng tài liệu này thay các câu hỏi mở của schema draft.

## Topic và payload

Topic: campus/v1/{building_id}/{device_id}/readings, QoS1, retain=false.
Consumer subscribe campus/v1/+/+/readings; reject retained message.
ID: 1–64 ký tự ASCII [A-Za-z0-9_-], phân biệt hoa thường. message_id UUID string, duy nhất toàn bộ dataset.
UTF-8 JSON object, tối đa 4096 bytes. Không chấp nhận field lạ, null, bool/string thay number, NaN/Infinity, JSON key lặp.
Bắt buộc schema_version="1.0", message_id, building_id, device_id, event_time, metric, value.
metric chỉ power_kw hoặc energy_kwh. value >=0.
event_time ISO8601 UTC có Z; tối đa microsecond; reject > received_at+5s. Không giới hạn tuổi dữ liệu cũ trong MVP.
energy_kwh bắt buộc interval_start UTC Z, interval_start < event_time.
power_kw không được có interval_start.
received_at không thuộc payload. Tên unit không nằm payload: Backend map metric sang kW/kWh.

Ví dụ power:
```json
{"schema_version":"1.0","message_id":"00000000-0000-4000-8000-000000000001","building_id":"BLD-A","device_id":"A-01","event_time":"2026-10-27T00:01:00Z","metric":"power_kw","value":12}
```
Ví dụ energy của phút vừa đo:
```json
{"schema_version":"1.0","message_id":"00000000-0000-4000-8000-000000000002","building_id":"BLD-A","device_id":"A-01","interval_start":"2026-10-27T00:00:00Z","event_time":"2026-10-27T00:01:00Z","metric":"energy_kwh","value":0.2}
```

## Ingest và dữ liệu đặc biệt

Thứ tự: size/JSON/schema -> topic/registry -> idempotency -> interval -> transaction.
Same message_id + cùng nội dung field hợp lệ (bỏ qua thứ tự JSON keys) = duplicate: không thêm reading/alert, không cập nhật last_seen.
Same message_id + nội dung khác = MESSAGE_ID_CONFLICT, không ghi đè.
Khác ID nhưng trùng (device,metric,event_time) = READING_CONFLICT, không tự cộng.
Energy interval không chồng lấn các interval đã lưu cho device; giao nhau chỉ tại biên được phép. Overlap = INTERVAL_OVERLAP, reject.
Invalid/unknown/topic mismatch = reject, không vào history/aggregate/status. Counter lỗi có mã; không publish lỗi vào topic readings.
Late = received_at-event_time >2*period. Out-of-order = event_time < max đã nhận của cùng device+metric.
Late/out-of-order hợp lệ vẫn lưu; history sort event_time; không thay max bằng thời điểm cũ.
Khi nhiều lỗi cùng tồn tại, trả/log lỗi đầu theo thứ tự kiểm tra; MQTT không có HTTP error response.

## Điện năng và tổng quan

energy_kwh là điện năng trong [interval_start,event_time), KHÔNG phải counter tích lũy.
Simulator tạo interval liên tiếp đúng period, trên lưới UTC bắt đầu từ mốc phút cho demo; power mỗi interval là hằng số mô phỏng.
energy = power_kw * duration_seconds / 3600. Dữ liệu thực trong tương lai có thể đo energy trực tiếp; Backend không kiểm tra hai metric phải bằng nhau và không suy energy nếu missing.

Summary(start,end):
- chọn energy interval có interval_start >= start và event_time <= end;
- cộng value theo device rồi building; không cộng power, không cộng duplicate;
- không chia tỷ lệ interval cắt biên; trả included_interval_count;
- coverage_ratio = tổng giây interval được chọn / ((end-start)*số device enabled của building);
- coverage = complete khi ratio=1, partial khi 0<ratio<1, none khi 0;
- energy_kwh=null khi không có interval, khác với 0 kWh đã đo;
- no enabled devices: ratio=0, coverage=none, energy=null;
- summary data_stale=true nếu bất kỳ enabled device stale hoặc chưa gửi.

Các interval không chồng nhau nên ratio <=1; thay registry/cấu hình cần dataset mới.
UI hiển thị điện năng ghi nhận và mức phủ, không gọi partial là tổng tiêu thụ đầy đủ.
Lịch sử vẫn lọc event_time theo [start,end); summary có thể tính interval kết thúc đúng end. Đây là hai ngữ nghĩa cố ý khác nhau, cần test biên.
Sai lệch số thực khi kiểm thử dùng sai số tuyệt đối 1e-9; UI làm tròn 3 chữ số nhưng không sửa giá trị API.

## Simulator và fixture

Seed: BLD-A/A-01, BLD-A/A-02, BLD-B/B-01; period=60s; threshold=10kW.
Seed và RNG seed phải xuất trong báo cáo để tái lập. CLI cần modes normal, duplicate, invalid, late, out-of-order, offline, load; có giới hạn duration/messages, không chạy vô hạn trong CI.
Normal: mỗi interval gửi hai metric; stable UUID khi retry, ID mới cho phép đo mới.
Duplicate: gửi nguyên bản hai lần. Invalid: missing field, wrong type, bad timestamp, unknown device, topic mismatch, oversized.
Late: event_time cách receive 1 giờ, interval không chồng fixture khác; phải late=true, không sửa timestamp thành now.
Out-of-order: gửi phút 3 rồi phút 2 với ID khác, cả hai hợp lệ; phút2 out_of_order=true.
Offline: dừng toàn bộ metric của A-02 ít nhất 3 chu kỳ, devices khác tiếp tục; tiếp tục gửi reading mới để phục hồi.
Load: cấu hình số device, rate, duration; lưu số logical messages và publish attempts riêng, không gọi duplicate là reading mới.
