# Backend API Contract — đầu ra cho Dashboard

- Issue nguồn: [#2 — Chốt yêu cầu Backend/API và luồng dữ liệu](https://github.com/nguyenthetai0012/SE2026---T06/issues/2)
- Đối chiếu yêu cầu giao diện: [`docs/requirements/dashboard.md`](../requirements/dashboard.md)
- Phụ trách soạn: Tài (Backend/API)
- Phối hợp rà soát: Sương (Dashboard), An (MQTT/timestamp), Ngọc (fixture/test)
- Trạng thái: **bản nháp để nhóm rà soát**; chưa được coi là contract đã duyệt cho đến khi xác nhận qua Pull Request.

Tài liệu này mô tả **hành vi và dữ liệu Backend phải cung cấp** để Frontend tích hợp các luồng Dashboard. Tên trường, endpoint, schema JSON, phương thức truyền, công thức kWh, ngưỡng cảnh báo và thời hạn offline **không** được trình bày như đã chốt.

---

## 1. Nguyên tắc thiết kế hợp đồng

Mỗi quyết định được đánh dấu một trong ba trạng thái:

| Nhãn | Ý nghĩa |
| --- | --- |
| **[ĐÃ XÁC NHẬN]** | Có trong issue #2, `dashboard.md`, hoặc phạm vi APP-05 đã ghi nhận; nhóm dùng làm ràng buộc. |
| **[ĐỀ XUẤT]** | Đề xuất từ comment Dashboard trên issue #2 hoặc từ phía Backend; dùng để thảo luận, chưa phải contract đã duyệt. |
| **[CÒN MỞ]** | Cần người phụ trách xác nhận; không được implement như đã chốt. |

### 1.1 Phạm vi Backend phải phủ

- **[ĐÃ XÁC NHẬN]** Backend hỗ trợ các chức năng: nhận dữ liệu cảm biến, quản lý danh mục thiết bị, truy vấn chuỗi thời gian, cảnh báo bất thường, trạng thái thiết bị offline.
- **[ĐÃ XÁC NHẬN]** Contract đầu ra phải đủ để Dashboard thực hiện FLOW-01 … FLOW-05 và kiểm tra AC-01 … AC-12 trong `docs/requirements/dashboard.md`.
- **[ĐÃ XÁC NHẬN]** Dashboard **hiển thị** dữ liệu Backend cung cấp; không tự tính tổng năng lượng khi chưa có công thức được duyệt; không tự định nghĩa ngưỡng/thuật toán phát hiện bất thường.
- **[ĐÃ XÁC NHẬN]** Tài liệu này **không** chốt MQTT broker, ngôn ngữ Backend, time-series DB, hay framework giao diện.

### 1.2 Cách ghi và giới hạn

- **[ĐÃ XÁC NHẬN]** Chưa tự đặt endpoint, tên trường/schema, phương thức truyền dữ liệu, múi giờ, công thức tổng hợp, ngưỡng cảnh báo hoặc thời hạn offline như quyết định đã duyệt.
- **[ĐÃ XÁC NHẬN]** Phần chưa thống nhất phải ghi **[CÒN MỞ]** hoặc **[ĐỀ XUẤT]**; không được viết như contract đã duyệt.
- **[ĐÃ XÁC NHẬN]** Mọi quyết định còn mở được liệt kê rõ; contract chỉ được coi là đã duyệt sau khi nhóm xác nhận qua PR.

### 1.3 Phân tách trách nhiệm dữ liệu

- **[ĐÃ XÁC NHẬN]** Frontend không suy ra trạng thái offline từ lỗi tải trang hoặc từ danh sách lịch sử rỗng (AC-11).
- **[ĐÃ XÁC NHẬN]** Backend phải cho Frontend phân biệt: thành công có dữ liệu, thành công nhưng rỗng, và lỗi (phục vụ AC-07, AC-08, AC-09).
- **[ĐỀ XUẤT]** API dùng timestamp UTC; giao diện hiển thị theo giờ Việt Nam.
- **[CÒN MỞ]** Múi giờ vận hành, quy ước biên khoảng thời gian (bao gồm/loại điểm đầu–cuối) và identifer chính thức của tòa nhà/thiết bị/cảm biến.

---

## 2. Hợp đồng theo luồng Dashboard

### 2.1 Tổng quan tòa nhà

**Luồng / AC:** FLOW-01; AC-01; AC-12.

**Mục đích:** Dashboard so sánh năng lượng các tòa nhà và chọn tòa nhà để xem chi tiết, **không** tự cộng từ bản ghi cảm biến.

#### Dữ liệu Backend cung cấp

| Nội dung | Trạng thái | Ghi chú |
| --- | --- | --- |
| Mỗi tòa nhà trong kết quả có định danh/tên ổn định để Frontend gắn đúng giá trị, không tráo giữa các tòa nhà | **[ĐÃ XÁC NHẬN]** | AC-01, AC-12 |
| Giá trị năng lượng do Backend cung cấp sẵn cho từng tòa nhà | **[ĐÃ XÁC NHẬN]** | Frontend không tự tính tổng |
| Đơn vị đi kèm giá trị | **[ĐỀ XUẤT]** | Đơn vị hiển thị: **kWh** (đề xuất Dashboard) |
| Khoảng thời gian áp dụng cho giá trị đó (mốc bắt đầu và kết thúc) | **[ĐÃ XÁC NHẬN]** là bắt buộc có khoảng; **[ĐỀ XUẤT]** mặc định **24 giờ gần nhất** | Truy vấn có mốc start/end |
| Trạng thái độ mới / dữ liệu cũ nếu Backend có thể cung cấp | **[CÒN MỞ]** | Chỉ hiển thị khi nguồn cung cấp; tiêu chí freshness chưa chốt |
| Công thức/metric quy đổi sang kWh (từ công suất, tích phân theo thời gian, hay metric sẵn có) | **[CÒN MỞ]** | Không được ngầm định trong contract này |

#### Hành vi

1. Dashboard yêu cầu tổng quan theo khoảng thời gian đang chọn (hoặc khoảng mặc định nếu người dùng chưa chọn).
2. Backend trả **một mục tổng quan cho mỗi tòa nhà** có trong phạm vi, gắn đúng giá trị, đơn vị và khoảng thời gian.
3. Nếu một tòa nhà không có số liệu trong khoảng đó, Backend vẫn phải cho Frontend biết đó là **thiếu dữ liệu của tòa nhà**, không được gán nhầm số liệu tòa khác (AC-12).
4. **[ĐỀ XUẤT]** Khi người dùng không chọn khoảng: Backend áp dụng 24 giờ gần nhất và **trả lại** khoảng đã dùng để Dashboard hiển thị.

#### Tiêu chí nghiệm thu (phía Backend, đối chiếu Dashboard)

- **AC-01:** Với ít nhất hai tòa nhà có giá trị khác nhau, mỗi tòa nhà xuất hiện đúng một mục; giá trị, đơn vị, khoảng thời gian khớp dữ liệu nguồn; không tráo giá trị.
- **AC-12:** Cùng một bộ dữ liệu đầu vào, giá trị tổng quan luôn gắn đúng tòa nhà; không trộn với thiết bị/cảnh báo/lịch sử của đối tượng khác.

---

### 2.2 Danh sách thiết bị và trạng thái offline

**Luồng / AC:** FLOW-02; AC-02; AC-05; AC-11.

**Mục đích:** Dashboard liệt kê thiết bị theo khuôn viên hoặc theo tòa nhà, thể hiện liên hệ thiết bị–tòa nhà và trạng thái kết nối do Backend cung cấp.

#### Dữ liệu Backend cung cấp

| Nội dung | Trạng thái | Ghi chú |
| --- | --- | --- |
| Định danh thiết bị ổn định | **[ĐÃ XÁC NHẬN]** | |
| Liên hệ thiết bị thuộc tòa nhà nào | **[ĐÃ XÁC NHẬN]** | AC-02 |
| Trạng thái online/offline do Backend xác định và trả về | **[ĐÃ XÁC NHẬN]** | Frontend không tự suy từ lỗi tải |
| Thời điểm liên lạc gần nhất (last-seen) | **[ĐỀ XUẤT]** | Hiển thị nếu được cung cấp; ý nghĩa phụ thuộc MQTT |
| Phạm vi lọc: toàn khuôn viên hoặc một tòa nhà | **[ĐÃ XÁC NHẬN]** | FLOW-02 |
| Quy tắc: offline khi không nhận dữ liệu trong **3 chu kỳ gửi dự kiến** | **[ĐỀ XUẤT]** từ Dashboard; **[CÒN MỞ]** chu kỳ gửi và cách Backend tính | An và Tài xác nhận |

#### Hành vi

1. Dashboard yêu cầu danh sách thiết bị theo phạm vi (toàn khuôn viên hoặc một tòa nhà).
2. Backend chỉ trả thiết bị thuộc phạm vi đó và giữ đúng liên hệ thiết bị–tòa nhà.
3. Thiết bị Backend đánh dấu offline phải nhận diện được độc lập với việc truy vấn lịch sử có rỗng hay không.
4. Lỗi tải danh sách **không** được Frontend (và không được contract này) diễn giải thành “mọi thiết bị offline” (AC-11).
5. **[ĐỀ XUẤT]** last-seen phản ánh lần Backend nhận dữ liệu hợp lệ gần nhất; không thay thế `event_time` của bản ghi đo.

#### Tiêu chí nghiệm thu

- **AC-02:** Khi dữ liệu có thiết bị thuộc từ hai tòa nhà trở lên, kết quả theo phạm vi đang xem chỉ gồm thiết bị thuộc phạm vi đó; liên hệ thiết bị–tòa nhà đúng.
- **AC-05:** Một thiết bị offline và một thiết bị online trong fixture: Backend gắn đúng từng trạng thái; không đảo nhãn.
- **AC-11:** Trạng thái offline độc lập với trạng thái tải của Dashboard; lỗi truy vấn không biến thành nhãn offline và ngược lại.

---

### 2.3 Lịch sử cảm biến theo chuỗi thời gian

**Luồng / AC:** FLOW-03; FLOW-05; AC-03; AC-06; AC-10.

**Mục đích:** Dashboard xem diễn biến phép đo và tra cứu lịch sử theo điều kiện thời gian đã thống nhất; Backend trả đúng bản ghi thuộc đối tượng và khoảng đã chọn.

#### Dữ liệu Backend cung cấp

| Nội dung | Trạng thái | Ghi chú |
| --- | --- | --- |
| Đối tượng truy vấn: thiết bị và/hoặc cảm biến được chọn | **[ĐÃ XÁC NHẬN]** | AC-03, AC-06 |
| Loại phép đo nếu nguồn có nhiều loại | **[ĐÃ XÁC NHẬN]** khi contract MQTT cung cấp | **[CÒN MỞ]** danh sách loại đo chính thức |
| Mỗi điểm: thời điểm đo, giá trị, đơn vị | **[ĐÃ XÁC NHẬN]** | |
| Khoảng truy vấn (bắt đầu–kết thúc) | **[ĐÃ XÁC NHẬN]** tối thiểu phải hỗ trợ khoảng thời gian | FLOW-05 |
| **`event_time`:** thời điểm đo; dùng để **lọc và sắp xếp** | **[ĐỀ XUẤT]** | An xác nhận ý nghĩa MQTT |
| **`received_at`:** thời điểm Backend nhận; dùng để nhận biết dữ liệu đến trễ; **không** thay `event_time` khi lọc | **[ĐỀ XUẤT]** | Backend giữ trường này |
| Timestamp trên API theo UTC | **[ĐỀ XUẤT]** | UI hiển thị giờ Việt Nam — việc UI, không đổi giá trị API |
| Dấu hiệu dữ liệu cũ / đến trễ | **[ĐỀ XUẤT]** Backend có thể gắn cờ dựa trên lệch `event_time` vs `received_at` hoặc tiêu chí freshness; **[CÒN MỞ]** ngưỡng | AC-10 |
| Bộ lọc khác ngoài khoảng thời gian (tòa nhà, loại đo, phân trang) | **[CÒN MỞ]** | Nhóm chốt trước khi xem là bắt buộc |

#### Hành vi

1. Dashboard gửi đối tượng và điều kiện thời gian (tối thiểu start/end).
2. Backend chỉ trả bản ghi của đối tượng đó có `event_time` nằm trong khoảng đã chọn (**[ĐỀ XUẤT]** quy tắc biên khoảng: **[CÒN MỞ]** inclusive/exclusive).
3. Mỗi bản ghi giữ `event_time`, giá trị, đơn vị; Backend **giữ** `received_at` để phân biệt trễ, kể cả khi Dashboard chưa hiển thị trường này.
4. Khi Backend đánh dấu cũ/đến trễ, Dashboard thể hiện nhãn trên đúng bản ghi và **không** trình bày như cập nhật mới nhất (AC-10).
5. Nếu không có bản ghi phù hợp: trả **thành công rỗng**, không trả lỗi (mục 2.5, AC-08).

#### Tiêu chí nghiệm thu

- **AC-03:** Một cảm biến có nhiều bản ghi; với một điều kiện truy vấn, Backend/Dashboard chỉ thể hiện bản ghi khớp cảm biến và điều kiện; mỗi bản ghi có thời gian, giá trị, đơn vị.
- **AC-06:** Tra cứu một đối tượng trong một khoảng thời gian không trả bản ghi ngoài khoảng; bản ghi gắn đúng đối tượng.
- **AC-10:** Fixture đánh dấu cũ/đến trễ: trạng thái đó được Backend cung cấp (hoặc suy ra theo quy tắc đã chốt) và đi kèm thời gian nguồn; không bị coi là bản mới nhất.

---

### 2.4 Phát hiện bất thường và cảnh báo

**Luồng / AC:** FLOW-04; AC-04.

**Mục đích:** Backend phát hiện và cung cấp cảnh báo; Dashboard chỉ hiển thị cảnh báo đã có, gắn đúng thiết bị/tòa nhà.

#### Dữ liệu Backend cung cấp

| Nội dung | Trạng thái | Ghi chú |
| --- | --- | --- |
| Backend tạo cảnh báo; Dashboard không tự phát hiện | **[ĐÃ XÁC NHẬN]** | `dashboard.md` mục FLOW-04 |
| Mô tả cảnh báo | **[ĐÃ XÁC NHẬN]** | |
| Thời điểm cảnh báo | **[ĐÃ XÁC NHẬN]** | **[CÒN MỞ]** dùng mốc phát hiện hay mốc `event_time` liên quan |
| Liên kết thiết bị và/hoặc tòa nhà | **[ĐÃ XÁC NHẬN]** nếu có trong dữ liệu nguồn | AC-04 |
| Mức độ (severity), trạng thái xử lý | **[CÒN MỞ]** | Chỉ đưa vào khi nhóm xác nhận |
| Ngưỡng / thuật toán phát hiện | **[CÒN MỞ]** | Không thuộc contract hiển thị; Ngọc/Tài chốt riêng |
| Thao tác xác nhận hoặc đóng cảnh báo trên Dashboard | **[ĐỀ XUẤT] không đưa vào MVP** | Không có API đóng/xác nhận trong phạm vi issue #2 |

#### Hành vi

1. Dashboard yêu cầu danh sách cảnh báo theo phạm vi được hỗ trợ (toàn khuôn viên hoặc lọc theo tòa nhà/thiết bị — **[CÒN MỞ]** bộ lọc chính thức).
2. Backend trả các cảnh báo đã tạo, mỗi cảnh báo gắn đối tượng liên quan và mô tả/thời điểm có sẵn.
3. Dashboard có thể điều hướng tới thiết bị/tòa nhà nếu định danh được cung cấp.
4. **MVP:** người dùng **không** xác nhận/đóng cảnh báo; Backend không cần hợp đồng hành động đó.

#### Tiêu chí nghiệm thu

- **AC-04:** Với một cảnh báo trong fixture, Backend cung cấp đủ để Dashboard hiển thị cảnh báo, liên kết đúng đối tượng, kèm các trường mô tả đã có trong contract. Quy tắc tạo cảnh báo được kiểm tra riêng, không thuộc AC-04.

---

### 2.5 Phân tách ba trạng thái kết quả truy vấn

**Luồng / AC:** AC-07; AC-08; AC-09 (áp dụng cho tổng quan, danh sách thiết bị, lịch sử, cảnh báo).

**Mục đích:** Frontend hiển thị đúng loading / không có dữ liệu / lỗi / retry; Backend phải phát ra tín hiệu phân biệt được, không gộp “rỗng” với “lỗi”.

| Kết quả | Ý nghĩa | Việc Frontend làm | Trạng thái quyết định |
| --- | --- | --- | --- |
| Thành công, có dữ liệu | Trả về một hoặc nhiều mục hợp lệ | Hiển thị dữ liệu; kết thúc trạng thái đang tải | **[ĐÃ XÁC NHẬN]** |
| Thành công, danh sách rỗng | Truy vấn hợp lệ, không có bản ghi thỏa điều kiện | Hiển thị **không có dữ liệu** + phạm vi truy vấn; **không** báo lỗi tải | **[ĐÃ XÁC NHẬN]** (AC-08) |
| Lỗi | Backend/kênh truyền không hoàn thành truy vấn | Hiển thị **lỗi**; cho phép **thử lại cùng điều kiện** | **[ĐÃ XÁC NHẬN]** (AC-09) |

#### Hành vi

1. Khi yêu cầu còn chờ phản hồi, Dashboard thể hiện đang tải; trạng thái này kết thúc khi có kết quả hoặc lỗi (AC-07). Đây chủ yếu là hành vi UI; Backend không được trả kết quả rỗng giả trong lúc chưa xử lý xong.
2. Thành công rỗng **không** dùng cùng tín hiệu với lỗi.
3. Khi lỗi, Frontend gửi lại **cùng** đối tượng, khoảng thời gian và bộ lọc hiện tại (AC-09). Backend phải xử lý idempotent ở mức truy vấn đọc: cùng điều kiện cho cùng ý nghĩa kết quả.
4. **[ĐÃ XÁC NHẬN]** Lỗi truy vấn không được Backend (hay Frontend) diễn giải thành thiết bị offline (AC-11).
5. **[CÒN MỞ]** Mã lỗi, định dạng thông báo, timeout và phân trang — chưa chốt; chỉ cần bảo đảm ba lớp kết quả trên vẫn tách được.

#### Tiêu chí nghiệm thu

- **AC-07:** Trong thời gian chờ, UI đang tải; kết thúc khi có kết quả hoặc lỗi.
- **AC-08:** Truy vấn thành công, danh sách rỗng → trạng thái không có dữ liệu, kèm phạm vi; không hiện lỗi tải.
- **AC-09:** Truy vấn thất bại → trạng thái lỗi + thao tác thử lại; lần thử lại dùng cùng điều kiện.

---

## 3. Câu hỏi mở — cần nhóm xác nhận

| ID | Câu hỏi | Ảnh hưởng | Người cần xác nhận |
| --- | --- | --- | --- |
| Q1 | Metric năng lượng tổng quan là gì và công thức ra kWh? | 2.1, AC-01 | Tài đề xuất; Sương đối chiếu hiển thị; An xác nhận nguồn MQTT |
| Q2 | Khoảng mặc định 24 giờ và quy ước biên start/end (inclusive)? | 2.1, 2.3 | Tài, Sương |
| Q3 | Múi giờ vận hành: API UTC, UI giờ Việt Nam có được chấp nhận? | 1.3, 2.3 | Cả nhóm |
| Q4 | Định danh chính thức của tòa nhà, thiết bị, cảm biến? | 2.1–2.4, AC-12 | An (MQTT), Tài (registry) |
| Q5 | Chu kỳ gửi dự kiến của simulator? Offline = 3 chu kỳ có chấp nhận được? | 2.2, AC-05 | **An**, Tài |
| Q6 | last-seen lấy từ `received_at` hay mốc khác? | 2.2 | An, Tài |
| Q7 | `event_time` vs `received_at` trên payload MQTT: tên và nghĩa cuối cùng? | 2.3, AC-10 | **An** |
| Q8 | Ngưỡng đánh dấu dữ liệu cũ / đến trễ? | 2.3, AC-10 | An, Tài, Sương |
| Q9 | Loại phép đo bắt buộc trên Dashboard (điện năng, công suất, …)? | 2.3 | An, Sương |
| Q10 | Ngưỡng/thuật toán tạo cảnh báo? | 2.4 | Tài, Ngọc (kiểm thử được) |
| Q11 | Có lọc cảnh báo theo tòa nhà/thiết bị/thời gian trong MVP không? | 2.4 | Sương, Tài |
| Q12 | Có đưa severity/trạng thái cảnh báo vào MVP không? | 2.4 | Cả nhóm — mặc định **chưa** |
| Q13 | Định dạng tín hiệu 3 trạng thái kết quả (không chốt HTTP status/schema trong bản này)? | 2.5 | Tài, Sương, Ngọc |
| Q14 | Bộ lọc lịch sử ngoài khoảng thời gian (phân trang, loại đo)? | FLOW-05 | Sương, Tài, Ngọc |

Những dòng trên **không** được implement như đã chốt cho đến khi chuyển sang **[ĐÃ XÁC NHẬN]** trên PR.

---

## 4. Checklist rà soát

Contract chỉ đóng issue #2 khi các mục dưới đây được xác nhận trên Pull Request.

### 4.1 Sương (@transuong630-web) — đối chiếu Dashboard

**Xác nhận phía Dashboard — Sương, 2026-10-22:** Sáu mục dưới đây được xác nhận ở mức nhu cầu hiển thị và hành vi, đối chiếu FLOW-01–05, AC-01–12 của `dashboard.md`. Sương đồng ý MVP chỉ xem cảnh báo, chưa cần thao tác đóng/xác nhận. Đây không phải phê duyệt toàn bộ API/schema hoặc các quyết định Q1–Q14; phần phụ thuộc MQTT, Backend và kiểm thử vẫn cần người phụ trách xác nhận. Retry giữ nguyên đối tượng, khoảng thời gian và bộ lọc; kết quả có thể thay đổi khi Backend nhận thêm dữ liệu, không yêu cầu hai lần trả dữ liệu giống hệt.

- [x] 2.1 đủ cho FLOW-01, AC-01, AC-12: giá trị + đơn vị + khoảng; Frontend không tự cộng.
- [x] 2.2 đủ cho FLOW-02, AC-02, AC-05, AC-11: danh sách theo phạm vi, offline do Backend, không nhầm với lỗi tải.
- [x] 2.3 đủ cho FLOW-03, FLOW-05, AC-03, AC-06, AC-10: lọc theo thời điểm đo, có thể hiện cũ/trễ khi nguồn cung cấp.
- [x] 2.4 đủ cho FLOW-04, AC-04; đồng ý MVP **không** đóng/xác nhận cảnh báo.
- [x] 2.5 đủ cho AC-07, AC-08, AC-09: có data / rỗng / lỗi + retry cùng điều kiện.
- [x] Không thiếu dữ liệu so với bảng màn hình trong `docs/requirements/dashboard.md`.

### 4.2 An (@NguyenThaiAn2810) — MQTT, timestamp, chu kỳ gửi

- [ ] Ý nghĩa thời điểm đo vs thời điểm nhận khớp simulator (đề xuất `event_time` / `received_at`).
- [ ] Chu kỳ gửi dự kiến và khả năng Backend suy ra offline (đề xuất 3 chu kỳ — **[CÒN MỞ]**).
- [ ] Dữ liệu đến trễ / sai thứ tự: Backend vẫn lọc theo thời điểm đo, giữ thời điểm nhận.
- [ ] Định danh tòa nhà/thiết bị/cảm biến trên payload không mâu thuẫn với registry Backend.
- [ ] Chưa coi topic/payload MQTT trong tài liệu này là schema đã duyệt (thuộc issue simulator/contract MQTT).

### 4.3 Ngọc (@ngochongnguyen) — fixture và kiểm thử

- [ ] Có thể dựng fixture: ≥2 tòa nhà giá trị khác nhau (AC-01, AC-12).
- [ ] Có thể dựng fixture: thiết bị thuộc ≥2 tòa nhà; một online, một offline (AC-02, AC-05, AC-11).
- [ ] Có thể dựng fixture: nhiều điểm thời gian, bản ghi ngoài khoảng, bản ghi cũ/đến trễ (AC-03, AC-06, AC-10).
- [ ] Có thể dựng fixture: một cảnh báo gắn đúng đối tượng (AC-04).
- [ ] Có thể giả lập ba kết quả truy vấn: có data, rỗng, lỗi (AC-07, AC-08, AC-09) mà không phụ thuộc stack chưa chốt.
- [ ] Các mục **[CÒN MỞ]** không bị test coi như đã chốt.

### 4.4 Tài — trước khi mở PR

- [x] Ghi contract vào `docs/contracts/backend-api.md`.
- [ ] Không chốt endpoint, tên trường, broker, ngôn ngữ, DB.
- [ ] Mỗi chức năng có mô tả hành vi và AC đối chiếu Dashboard.
- [ ] Comment trên issue #2 khi có PR, nêu rõ phần **[ĐỀ XUẤT]** / **[CÒN MỞ]**.

---

## 5. Những gì tài liệu này cố ý không chốt

- Đường dẫn API, verb, payload JSON, mã trạng thái cụ thể.
- Tên field cuối cùng trên MQTT hoặc HTTP.
- Sản phẩm MQTT broker, runtime Backend, cơ sở dữ liệu chuỗi thời gian.
- Công thức kWh, ngưỡng cảnh báo, số giây/phút timeout offline.
- Chính sách xác thực, phân quyền, cơ chế đẩy realtime (polling/websocket).

Các mục trên sẽ vào `docs/contracts/` hoặc `docs/decisions/` riêng **sau** khi nhóm xác nhận.

---

## 6. Nguồn

- Issue #2 (mô tả + comment đề xuất Dashboard, 2026-10-14).
- `docs/requirements/dashboard.md` (FLOW-01 … FLOW-05, AC-01 … AC-12).
- `README.md` — phạm vi APP-05 đã xác nhận; stack và ngưỡng vẫn cần nhóm duyệt.
