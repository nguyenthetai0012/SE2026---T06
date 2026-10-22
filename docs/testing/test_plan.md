# APP-05 Smart Campus Energy Dashboard — Kế hoạch kiểm thử
## 1. Mục đích

Tài liệu này xác định kế hoạch kiểm thử ban đầu cho hệ thống Bảng điều khiển Năng lượng Khuôn viên Thông minh APP-05 (Smart Campus Energy Dashboard). Tài liệu xác định các hạng mục kiểm thử chính, các tình huống kiểm thử, điều kiện đầu vào, kết quả mong đợi và các bước kiểm tra tích hợp liên tục (CI) được đề xuất.

Dự án hiện đang ở giai đoạn lập kế hoạch ban đầu. Các tình huống kiểm thử sẽ được điều chỉnh khi nhóm thống nhất về kiến trúc hệ thống, hợp đồng dữ liệu, công nghệ sử dụng và tiêu chí nghiệm thu.

## 2. Phạm vi

Hoạt động kiểm thử sẽ bao gồm các hạng mục sau:

- Tiếp nhận dữ liệu MQTT và kiểm tra tính hợp lệ của dữ liệu đầu vào.
- Đăng ký thiết bị và quản lý trạng thái thiết bị.
- Phát hiện thiết bị ngoại tuyến và khôi phục trạng thái hoạt động.
- Cảnh báo năng lượng và phát hiện các chỉ số bất thường.
- Truy vấn dữ liệu chuỗi thời gian trong lịch sử.
- Hiển thị và cập nhật dữ liệu trên bảng điều khiển.
- Xử lý thông điệp đến muộn, không đúng thứ tự và bị trùng lặp.
- Kiểm thử hiệu năng và khả năng chịu tải.
- Kiểm tra bảo mật cơ bản và cấu hình hệ thống.

## 3. Chiến lược kiểm thử

Nhóm nên kết hợp các phương pháp kiểm thử sau:

- **Kiểm thử đơn vị (Unit testing):** Kiểm tra từng hàm hoặc thành phần riêng lẻ, chẳng hạn như hàm kiểm tra tính hợp lệ của dữ liệu đầu vào và hàm đánh giá điều kiện cảnh báo.
- **Kiểm thử tích hợp (Integration testing):** Kiểm tra khả năng giao tiếp giữa các thành phần tiếp nhận dữ liệu, lưu trữ, xử lý cảnh báo và các thành phần khác của hệ thống.
- **Kiểm thử API hoặc hợp đồng dữ liệu (API/Contract testing):** Kiểm tra xem dữ liệu đầu vào, đầu ra và phản hồi lỗi có tuân thủ các hợp đồng đã được nhóm phê duyệt hay không.
- **Kiểm thử đầu cuối (End-to-end testing):** Kiểm tra các quy trình sử dụng quan trọng, từ khi dữ liệu cảm biến được gửi đến cho đến khi dữ liệu hiển thị trên bảng điều khiển và cảnh báo được trình bày.
- **Kiểm thử hiệu năng (Performance testing):** Đo lường hoạt động của hệ thống theo tốc độ gửi thông điệp và khối lượng dữ liệu đã được thống nhất.
- **Kiểm thử bảo mật (Security testing):** Kiểm tra tính hợp lệ của dữ liệu đầu vào, cơ chế kiểm soát truy cập nếu có, việc quản lý thông tin bí mật và cách hệ thống phản hồi khi xảy ra lỗi.

Ngôn ngữ lập trình và khung kiểm thử hiện chưa được chốt. Các công cụ cụ thể chỉ nên được lựa chọn sau khi nhóm xác nhận công nghệ sử dụng.

## 4. Môi trường kiểm thử và điều kiện tiên quyết

Trước khi thực hiện kiểm thử, nhóm cần thống nhất các nội dung sau:

- Kiến trúc ứng dụng và các giao diện được hỗ trợ.
- Cấu trúc topic MQTT và lược đồ thông điệp.
- Các trường dữ liệu cảm biến bắt buộc, đơn vị đo, dấu thời gian và quy tắc kiểm tra tính hợp lệ.
- Quy tắc đăng ký và định danh thiết bị.
- Chính sách xử lý thông điệp trùng lặp, đến muộn và không đúng thứ tự.
- Ngưỡng thời gian xác định thiết bị ngoại tuyến và hành vi khôi phục.
- Ngưỡng cảnh báo và quy tắc xóa hoặc kết thúc cảnh báo.
- Giới hạn truy vấn lịch sử và quy ước múi giờ.
- Số lượng thiết bị đồng thời dự kiến, tốc độ gửi thông điệp và các mục tiêu hiệu năng.

Các bài kiểm thử cần được thực hiện trong môi trường có kiểm soát và sử dụng dữ liệu cảm biến tổng hợp. Không được sử dụng thông tin đăng nhập của môi trường sản xuất hoặc dữ liệu nhạy cảm thực tế.

## 5. Ma trận kiểm thử

| Mã | Hạng mục | Tình huống kiểm thử | Phương pháp xác minh |
|---|---|---|---|
| TC-01 | Tiếp nhận dữ liệu | Gửi một thông điệp cảm biến hợp lệ | Kiểm thử tích hợp: xác minh thông điệp được chấp nhận và xử lý theo hợp đồng đã được phê duyệt |
| TC-02 | Tiếp nhận dữ liệu | Gửi thông điệp thiếu trường dữ liệu bắt buộc | Kiểm thử hợp đồng: xác minh thông điệp bị từ chối hoặc được xử lý theo quy tắc kiểm tra dữ liệu đã thống nhất |
| TC-03 | Tiếp nhận dữ liệu | Gửi thông điệp có kiểu dữ liệu hoặc đơn vị đo không hợp lệ | Kiểm thử hợp đồng: xác minh dữ liệu không hợp lệ không bị âm thầm chuyển thành một chỉ số hợp lệ |
| TC-04 | Danh mục thiết bị | Gửi dữ liệu từ thiết bị chưa được đăng ký | Kiểm thử tích hợp: xác minh hành vi xử lý tuân theo chính sách đăng ký thiết bị đã được phê duyệt |
| TC-05 | Trạng thái thiết bị | Ngừng gửi thông điệp từ một thiết bị đã đăng ký | Kiểm thử tích hợp: xác minh thiết bị chuyển sang trạng thái ngoại tuyến theo thời gian chờ đã thống nhất |
| TC-06 | Trạng thái thiết bị | Tiếp tục gửi thông điệp từ thiết bị đang ngoại tuyến | Kiểm thử tích hợp: xác minh quá trình khôi phục tuân theo quy tắc chuyển trạng thái đã thống nhất |
| TC-07 | Cảnh báo | Gửi chỉ số vượt ngưỡng cảnh báo đã thống nhất | Kiểm thử tích hợp: xác minh cảnh báo dự kiến được tạo |
| TC-08 | Cảnh báo | Gửi chỉ số thấp hơn ngưỡng cảnh báo | Kiểm thử tích hợp: xác minh không tạo cảnh báo mới dựa trên ngưỡng đó, trừ khi có quy tắc khác được áp dụng |
| TC-09 | Dữ liệu lịch sử | Truy vấn dữ liệu trong một khoảng thời gian hợp lệ | Kiểm thử API/tích hợp: xác minh dữ liệu và dấu thời gian trả về khớp với dữ liệu đã lưu |
| TC-10 | Dữ liệu lịch sử | Truy vấn với khoảng thời gian không hợp lệ hoặc thời điểm bắt đầu sau thời điểm kết thúc | Kiểm thử API: xác minh yêu cầu được kiểm tra tính hợp lệ và hệ thống trả về phản hồi phù hợp |
| TC-11 | Bảng điều khiển | Hiển thị chỉ số và trạng thái của các thiết bị hiện có | Kiểm thử đầu cuối: đối chiếu giá trị và trạng thái hiển thị với dữ liệu kiểm thử đã biết |
| TC-12 | Bảng điều khiển | Làm mới hoặc cập nhật các chỉ số mới nhận được | Kiểm thử đầu cuối: xác minh bảng điều khiển phản ánh dữ liệu mới theo cơ chế cập nhật đã thống nhất |
| TC-13 | Thứ tự dữ liệu | Gửi các chỉ số theo thứ tự dấu thời gian không tăng dần | Kiểm thử tích hợp: xác minh dữ liệu lưu trữ và kết quả truy vấn tuân theo chính sách sắp xếp đã thống nhất |
| TC-14 | Tính kịp thời của dữ liệu | Gửi một chỉ số đến muộn hơn thời điểm nhận dữ liệu thông thường | Kiểm thử tích hợp: xác minh dữ liệu đến muộn được xử lý theo chính sách tiếp nhận dữ liệu và cảnh báo đã phê duyệt |
| TC-15 | Xử lý dữ liệu trùng lặp | Gửi cùng một thông điệp nhiều lần | Kiểm thử tích hợp: xác minh việc xử lý thông điệp trùng lặp tuân theo chính sách loại bỏ dữ liệu trùng đã thống nhất |
| TC-16 | Tải hệ thống | Tăng tốc độ gửi thông điệp đầu vào đến mức mục tiêu đã thống nhất | Kiểm thử hiệu năng: đo thông lượng, độ trễ, tỷ lệ lỗi và mức sử dụng tài nguyên |
| TC-17 | Bảo mật | Gửi dữ liệu có định dạng sai hoặc kích thước lớn bất thường | Kiểm thử bảo mật/tích hợp: xác minh dữ liệu được xử lý an toàn, không gây sập hệ thống hoặc tiêu tốn tài nguyên mất kiểm soát |
| TC-18 | Cấu hình | Khởi chạy một thành phần khi thiếu cấu hình bắt buộc | Kiểm thử khởi động: xác minh hệ thống đưa ra thông báo lỗi rõ ràng và không để lộ thông tin bí mật |

## 6. Các tình huống kiểm thử chi tiết cho trường hợp biên

### 6.1. Dữ liệu đến muộn và không đúng thứ tự

**Dữ liệu đầu vào:**

1. Gửi chỉ số A của thiết bị D1 với dấu thời gian sự kiện là 10:00.
2. Gửi chỉ số B của thiết bị D1 với dấu thời gian sự kiện là 10:02.
3. Sau khi chỉ số B đã được nhận, gửi chỉ số C của thiết bị D1 với dấu thời gian sự kiện là 10:01.

**Kết quả mong đợi:**

- Hệ thống xử lý các thông điệp theo chính sách về thời điểm sự kiện và thời điểm nhận dữ liệu đã được nhóm phê duyệt.
- Các truy vấn lịch sử trả về chỉ số theo thứ tự đã thống nhất.
- Chỉ số đến muộn không được âm thầm ghi đè lên chỉ số mới hơn, trừ khi hành vi đó đã được quy định rõ.
- Việc đánh giá cảnh báo tuân theo chính sách đã thống nhất đối với dữ liệu đến muộn.

**Quyết định cần thống nhất:** Nhóm phải xác định dữ liệu đến muộn sẽ được chấp nhận, từ chối hay lưu kèm nhãn nhận diện dữ liệu đến muộn, đồng thời xác định cách dữ liệu này ảnh hưởng đến việc xử lý cảnh báo.

### 6.2. Thiết bị ngoại tuyến

**Dữ liệu đầu vào:**

1. Đăng ký thiết bị D1.
2. Gửi các chỉ số hợp lệ từ D1.
3. Ngừng gửi chỉ số trong thời gian dài hơn ngưỡng thời gian xác định ngoại tuyến đã thống nhất.
4. Tiếp tục gửi các chỉ số hợp lệ từ thiết bị.

**Kết quả mong đợi:**

- Ban đầu, D1 được báo cáo là đang trực tuyến sau khi hệ thống xác nhận thiết bị đã giao tiếp hợp lệ.
- D1 được chuyển sang trạng thái ngoại tuyến theo ngưỡng thời gian và quy tắc trạng thái đã thống nhất.
- D1 được khôi phục theo chính sách kết nối lại đã thống nhất.
- Bảng điều khiển hiển thị trạng thái thiết bị tương ứng.

**Quyết định cần thống nhất:** Nhóm phải thống nhất ngưỡng thời gian ngoại tuyến, cơ chế gửi tín hiệu duy trì kết nối (heartbeat) và điều kiện khôi phục trạng thái.

### 6.3. Kiểm thử tải

**Dữ liệu đầu vào:**

1. Tạo dữ liệu chỉ số tổng hợp cho số lượng thiết bị đã thống nhất.
2. Tăng tốc độ gửi thông điệp theo từng giai đoạn có kiểm soát.
3. Chạy mỗi giai đoạn trong khoảng thời gian đã thống nhất.
4. Ghi nhận thông lượng, độ trễ xử lý, tỷ lệ lỗi và mức sử dụng tài nguyên.

**Kết quả mong đợi:**

- Hệ thống được đánh giá dựa trên các mục tiêu hiệu năng có thể đo lường mà nhóm đã thống nhất.
- Các lỗi, thông điệp bị mất và độ trễ xử lý được ghi nhận.
- Báo cáo kiểm thử xác định rõ số lượng thiết bị, tốc độ gửi thông điệp, thời lượng và môi trường đã sử dụng để kiểm thử.

**Quyết định cần thống nhất:** Nhóm phải xác định số lượng thiết bị mục tiêu, tốc độ gửi thông điệp, thời lượng kiểm thử, tỷ lệ lỗi chấp nhận được và ngưỡng độ trễ trước khi kết luận hệ thống đạt yêu cầu kiểm thử tải.

## 7. Dữ liệu kiểm thử và bằng chứng

Sử dụng các chỉ số cảm biến tổng hợp với mã định danh thiết bị, giá trị, đơn vị đo và dấu thời gian đã biết trước.

Đối với mỗi bài kiểm thử đã thực hiện, cần ghi lại:

- Mã tình huống kiểm thử.
- Môi trường và phiên bản phần mềm.
- Dữ liệu đầu vào và cấu hình liên quan.
- Kết quả thực tế và kết quả mong đợi.
- Trạng thái đạt/không đạt.
- Nhật ký hệ thống, ảnh chụp màn hình hoặc đầu ra kiểm thử khi phù hợp.
- Liên kết đến lỗi hoặc issue nếu bài kiểm thử thất bại.

Không được đánh dấu một bài kiểm thử là đạt cho đến khi bài kiểm thử đã được thực hiện và kết quả thực tế đã được đối chiếu.

## 8. Đề xuất CI ban đầu

Sau khi nhóm xác nhận ngôn ngữ lập trình, khung kiểm thử và các lệnh cần chạy trong repository, GitHub Actions nên được cấu hình để thực hiện các bước kiểm tra phù hợp khi có pull request và khi có thay đổi được đẩy lên các nhánh đã thống nhất.

Các giai đoạn CI được đề xuất:

1. **Checkout mã nguồn:** Lấy mã nguồn của repository về môi trường chạy CI.
2. **Thiết lập môi trường:** Cài đặt môi trường chạy và các thư viện phụ thuộc theo hướng dẫn thiết lập đã được dự án ghi lại.
3. **Kiểm tra tĩnh:** Chạy công cụ định dạng mã, công cụ phân tích lỗi mã nguồn và các công cụ phân tích tĩnh phù hợp đã được thống nhất.
4. **Kiểm thử đơn vị:** Chạy các bài kiểm thử đơn vị tự động.
5. **Kiểm thử hợp đồng và tích hợp:** Chạy các bài kiểm thử có thể thực thi ổn định trong CI với những dịch vụ cần thiết hoặc các thành phần thay thế phục vụ kiểm thử.
6. **Xây dựng hoặc xác thực:** Chạy lệnh xây dựng hoặc xác thực được dự án tài liệu hóa, nếu có.
7. **Báo cáo kiểm thử:** Lưu giữ đầu ra kiểm thử và nhật ký lỗi hữu ích mà không để lộ thông tin xác thực hoặc dữ liệu nhạy cảm.

Quy trình CI phải sử dụng công nghệ và các lệnh thực tế của dự án. Không thêm quy trình CI dành riêng cho một ngôn ngữ lập trình trước khi nhóm thống nhất về công nghệ và khung kiểm thử.

## 9. Các cân nhắc về bảo mật

- Tuyệt đối không đưa mật khẩu, mã thông báo, khóa riêng tư hoặc thông tin xác thực của môi trường sản xuất vào repository.
- Lưu trữ thông tin bí mật cần thiết cho CI trong GitHub Actions Secrets hoặc một hệ thống quản lý bí mật đã được phê duyệt.
- Kiểm tra tính hợp lệ của thông điệp đầu vào trước khi xử lý.
- Tránh ghi thông tin xác thực hoặc dữ liệu nhạy cảm không cần thiết vào nhật ký hệ thống.
- Xác minh các yêu cầu về xác thực và phân quyền sau khi những yêu cầu này được xác định.
- Tách biệt môi trường kiểm thử khỏi hệ thống sản xuất.

## 10. Rủi ro và các câu hỏi còn bỏ ngỏ

Các vấn đề sau cần được thống nhất trước khi hoàn thiện kế hoạch kiểm thử:

- Backend, frontend, cơ sở dữ liệu và MQTT broker nào sẽ được sử dụng?
- Lược đồ thông điệp cảm biến và cấu trúc topic nào đã được phê duyệt?
- Thông điệp trùng lặp được xác định và xử lý như thế nào?
- Chính sách xử lý chỉ số đến muộn và không đúng thứ tự là gì?
- Ngưỡng cảnh báo và cơ chế kết thúc hoặc khôi phục cảnh báo được xác định như thế nào?
- Ngưỡng thời gian nào được sử dụng để xác định thiết bị ngoại tuyến?
- Giới hạn truy vấn dữ liệu lịch sử và quy tắc múi giờ là gì?
- Số lượng thiết bị, tốc độ gửi thông điệp, độ trễ và tỷ lệ lỗi mục tiêu nào được xem là mức hiệu năng chấp nhận được?
- Dự án sẽ sử dụng ngôn ngữ lập trình, khung kiểm thử và các lệnh CI nào?

## 11. Rà soát và bảo trì

Tài liệu này là đề xuất ban đầu và cần được cập nhật khi các yêu cầu và hợp đồng dữ liệu được phê duyệt.


- Các tình huống liên quan đến Backend cần được Tài rà soát.
- Các tình huống liên quan đến Simulator và việc tạo dữ liệu cần được An rà soát.
- Nhóm cần xác nhận phạm vi kiểm thử, tiêu chí nghiệm thu và phương án CI trước khi triển khai.

Chỉ bổ sung kết quả kiểm thử và thông tin cụ thể về triển khai sau khi các bài kiểm thử hoặc bước kiểm tra tương ứng đã thực sự được thực hiện.
