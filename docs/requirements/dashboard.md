# Yêu cầu Dashboard Smart Campus Energy

- Issue nguồn: [#4 — Ghi yêu cầu và luồng người dùng cho Dashboard](https://github.com/nguyenthetai0012/SE2026---T06/issues/4)
- Trạng thái: yêu cầu ban đầu để nhóm rà soát; các điểm chưa được xác nhận được ghi riêng ở cuối tài liệu.

## 1. Mục tiêu và phạm vi

Dashboard giúp người dùng theo dõi tiêu thụ năng lượng của các tòa nhà trong khuôn viên, xem dữ liệu cảm biến theo thời gian, nhận biết cảnh báo bất thường và thiết bị offline, đồng thời tra cứu dữ liệu lịch sử.

Trong phạm vi Issue #4, Dashboard cần hỗ trợ:

1. Xem tổng quan năng lượng theo từng tòa nhà.
2. Xem danh sách thiết bị và biết thiết bị thuộc tòa nhà nào.
3. Xem dữ liệu cảm biến theo thời gian.
4. Xem các cảnh báo bất thường đã được hệ thống cung cấp.
5. Nhận biết thiết bị có trạng thái offline.
6. Tra cứu lịch sử dữ liệu theo các điều kiện truy vấn mà nhóm thống nhất.

Tài liệu này không chọn framework giao diện, cơ sở dữ liệu, giao thức, cách tính bất thường, đơn vị đo hoặc chính sách thời gian thực.

## 2. Yêu cầu theo màn hình

| Màn hình | Mục đích | Dữ liệu cần hiển thị ở mức yêu cầu | Tiêu chí nghiệm thu liên quan |
| --- | --- | --- | --- |
| Tổng quan theo tòa nhà | Giúp người dùng so sánh và chọn tòa nhà cần xem chi tiết. | Tên/định danh tòa nhà; giá trị năng lượng được nguồn dữ liệu cung cấp; đơn vị và khoảng thời gian tương ứng; trạng thái độ mới nếu nguồn cung cấp. Không tự tính tổng khi chưa có công thức được duyệt. | AC-01; điều hướng sang danh sách/chi tiết tòa nhà theo FLOW-01. |
| Danh sách thiết bị | Giúp người dùng tìm thiết bị trong toàn khuôn viên hoặc tòa nhà và nhận biết trạng thái kết nối. | Tên/định danh thiết bị; tòa nhà liên quan; trạng thái online/offline do nguồn dữ liệu cung cấp; lần liên lạc gần nhất nếu contract có trường này. | AC-02, AC-05, AC-11. |
| Chi tiết cảm biến và lịch sử | Giúp người dùng xem diễn biến phép đo và tra cứu theo thời gian. | Thiết bị/cảm biến được chọn; loại phép đo; các điểm dữ liệu gồm thời điểm đo, giá trị và đơn vị theo contract; khoảng truy vấn; dấu hiệu dữ liệu cũ/đến trễ nếu nguồn cung cấp. | AC-03, AC-06, AC-10. |
| Cảnh báo | Giúp người dùng xem bất thường do hệ thống đã phát hiện và xác định đối tượng liên quan. | Thông tin cảnh báo do Backend cung cấp; tối thiểu liên kết được với thiết bị hoặc tòa nhà nếu có trong contract, cùng thời điểm và mô tả có sẵn. Mức độ/ trạng thái chỉ hiển thị nếu nhóm thống nhất và nguồn cung cấp. | AC-04; điều hướng tới thiết bị/tòa nhà liên quan nếu được hỗ trợ. |

Các tên trường cụ thể, công thức năng lượng, mức độ cảnh báo và tiêu chí freshness/offline tiếp tục chờ contract/decisions được nhóm duyệt; bảng này không tự định nghĩa schema.

## 3. Luồng người dùng chính

### FLOW-01 — Xem tổng quan theo tòa nhà

1. Người dùng mở Dashboard.
2. Dashboard tải dữ liệu tổng quan.
3. Dashboard hiển thị một mục tổng quan cho mỗi tòa nhà có trong kết quả, gắn đúng giá trị năng lượng, đơn vị và khoảng thời gian do nguồn dữ liệu cung cấp.
4. Người dùng chọn một tòa nhà để đi đến danh sách thiết bị hoặc dữ liệu chi tiết của tòa nhà đó.

### FLOW-02 — Xem danh sách thiết bị và trạng thái

1. Người dùng mở danh sách thiết bị của khuôn viên hoặc một tòa nhà.
2. Dashboard hiển thị các thiết bị trong phạm vi được chọn và mối liên hệ với tòa nhà.
3. Thiết bị được nguồn dữ liệu đánh dấu offline có nhãn/trạng thái offline dễ nhận biết.
4. Người dùng có thể mở lịch sử của thiết bị nếu nguồn dữ liệu và điều hướng được nhóm thống nhất hỗ trợ.

### FLOW-03 — Xem dữ liệu cảm biến theo thời gian

1. Người dùng chọn cảm biến hoặc thiết bị cần xem.
2. Người dùng chọn khoảng thời gian nếu bộ lọc thời gian được thống nhất cho giao diện.
3. Dashboard hiển thị các giá trị cảm biến cùng thời điểm đo và đơn vị do contract dữ liệu cung cấp.
4. Khi dữ liệu được đánh dấu cũ hoặc đến trễ, Dashboard thể hiện trạng thái đó cạnh dữ liệu liên quan.

### FLOW-04 — Xem cảnh báo bất thường

1. Người dùng mở khu vực cảnh báo.
2. Dashboard hiển thị các cảnh báo do hệ thống cung cấp, gắn với tòa nhà/thiết bị và thông tin mô tả có trong contract đã duyệt.
3. Người dùng có thể mở đối tượng liên quan để xem thêm thông tin nếu điều hướng đó được nhóm thống nhất hỗ trợ.

Dashboard trong phạm vi này hiển thị cảnh báo đã được tạo; tài liệu không định nghĩa ngưỡng hay thuật toán phát hiện bất thường.

### FLOW-05 — Tra cứu lịch sử

1. Người dùng chọn đối tượng cần tra cứu trong các phạm vi được hỗ trợ.
2. Người dùng nhập/chọn điều kiện truy vấn đã được nhóm thống nhất, tối thiểu gồm khoảng thời gian.
3. Dashboard gửi yêu cầu và hiển thị các bản ghi trả về cùng dấu thời gian, giá trị và đơn vị sẵn có.
4. Nếu không có bản ghi phù hợp, Dashboard hiển thị trạng thái không có dữ liệu cho điều kiện đã chọn.

## 4. Trạng thái giao diện cần xử lý

| Trạng thái | Cách Dashboard cần thể hiện |
| --- | --- |
| Đang tải | Cho biết nội dung đang được tải; không hiển thị nhầm trạng thái rỗng trước khi có kết quả. |
| Không có dữ liệu | Nêu rõ phạm vi/điều kiện đang xem không có bản ghi; phân biệt với lỗi tải dữ liệu. |
| Lỗi tải dữ liệu | Báo rằng dữ liệu không tải được; không trình bày lỗi như kết quả rỗng. Có thao tác thử tải lại yêu cầu hiện tại. |
| Dữ liệu cũ/đến trễ | Gắn dấu hiệu dễ nhận biết vào dữ liệu bị đánh dấu cũ hoặc đến trễ; giữ thông tin thời gian có trong contract và không trình bày dữ liệu đó như vừa cập nhật. |
| Thiết bị offline | Gắn trạng thái offline với đúng thiết bị và tòa nhà; không đồng nhất offline với lỗi tải trang hoặc không có dữ liệu lịch sử. |

Ngưỡng xác định dữ liệu cũ, cách nhận biết dữ liệu đến trễ, thời điểm dùng để sắp xếp và điều kiện xác định thiết bị offline cần được nhóm chốt trong contract hoặc quyết định liên quan. Giao diện sử dụng trạng thái do nguồn dữ liệu đã thống nhất cung cấp.

## 5. Tiêu chí nghiệm thu

Có thể kiểm tra các tiêu chí dưới đây bằng bộ dữ liệu kiểm thử có kiểm soát. Tên trường và giá trị cụ thể phải theo contract được nhóm duyệt; không suy ra schema mới từ tài liệu này.

| ID | Tiêu chí kiểm tra |
| --- | --- |
| AC-01 | Với kết quả tổng quan có ít nhất hai tòa nhà và giá trị khác nhau, Dashboard hiển thị đúng một mục cho mỗi tòa nhà và gắn đúng giá trị, đơn vị, khoảng thời gian nguồn dữ liệu trả về; không tráo giá trị giữa các tòa nhà. |
| AC-02 | Với danh sách thiết bị thuộc từ hai tòa nhà trở lên, Dashboard chỉ hiển thị thiết bị trong phạm vi đang xem và thể hiện đúng liên hệ thiết bị–tòa nhà theo dữ liệu đầu vào. |
| AC-03 | Với một cảm biến có nhiều bản ghi thời gian và một điều kiện truy vấn đã chọn, Dashboard chỉ hiển thị bản ghi phù hợp với cảm biến/điều kiện đó; mỗi bản ghi hiển thị thời gian, giá trị và đơn vị nếu các trường này có trong contract. |
| AC-04 | Với một cảnh báo được cung cấp trong fixture kiểm thử, Dashboard hiển thị cảnh báo và liên kết đúng đối tượng liên quan cùng các trường mô tả mà contract đã duyệt cung cấp. Quy tắc tạo cảnh báo được kiểm tra riêng, không thuộc tiêu chí này. |
| AC-05 | Với một thiết bị có trạng thái offline và một thiết bị online, Dashboard đánh dấu đúng thiết bị offline và không đánh dấu nhầm thiết bị online. |
| AC-06 | Khi tra cứu một đối tượng trong một khoảng thời gian, Dashboard không hiển thị bản ghi ngoài điều kiện truy vấn và gắn đúng bản ghi trả về với đối tượng tương ứng. |
| AC-07 | Khi yêu cầu còn đang chờ phản hồi, Dashboard thể hiện trạng thái đang tải; trạng thái này kết thúc khi nhận được kết quả hoặc lỗi. |
| AC-08 | Khi truy vấn thành công nhưng trả về danh sách rỗng, Dashboard hiển thị trạng thái không có dữ liệu và phạm vi truy vấn; không hiển thị thông báo lỗi tải dữ liệu. |
| AC-09 | Khi truy vấn thất bại, Dashboard hiển thị trạng thái lỗi thay vì trạng thái rỗng và có thao tác thử lại. Khi người dùng thử lại, Dashboard gửi lại cùng truy vấn và điều kiện hiện tại. |
| AC-10 | Khi fixture đánh dấu dữ liệu là cũ hoặc đến trễ theo trạng thái đã thống nhất, Dashboard thể hiện nhãn tương ứng trên dữ liệu đó và giữ thời gian nguồn cung cấp; dữ liệu không bị trình bày như bản cập nhật mới nhất. |
| AC-11 | Trạng thái offline của thiết bị được hiển thị độc lập với trạng thái tải dữ liệu của Dashboard; lỗi tải dữ liệu không tự biến thành nhãn thiết bị offline và ngược lại. |
| AC-12 | Với cùng dữ liệu đầu vào, các giá trị trên tổng quan, dữ liệu theo thời gian, cảnh báo và lịch sử luôn gắn với đúng tòa nhà/thiết bị; không trộn dữ liệu giữa các đối tượng. |

## 6. Các điểm cần nhóm xác nhận

Để hoàn thiện contract và giao diện, nhóm cần thống nhất:

- Metric năng lượng, đơn vị, cách tổng hợp và khoảng thời gian mặc định của tổng quan.
- Các bộ lọc tra cứu được hỗ trợ, cách tính biên khoảng thời gian và múi giờ.
- Trường nhận diện tòa nhà, thiết bị, cảm biến và các trường thời gian/đơn vị có sẵn.
- Cách phân biệt thời điểm đo với thời điểm nhận dữ liệu; tiêu chí đánh dấu cũ/đến trễ.
- Trạng thái và các trường cảnh báo được cung cấp cho Dashboard; ngưỡng/thuật toán phát hiện thuộc quyết định riêng.
- Quy tắc xác định offline và dữ liệu last-seen nếu có.
- Hình thức trình bày dữ liệu theo thời gian và hành vi tải lại/cập nhật.

Trước khi coi tài liệu là yêu cầu được duyệt, Tài và Ngọc rà soát tính khả thi với dữ liệu/API và khả năng kiểm thử theo Issue #4.
