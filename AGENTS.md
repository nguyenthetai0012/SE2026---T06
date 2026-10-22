# 🤖 AGENTS.md - Quy định & Hướng dẫn cho AI Agents

> **Dự án:** APP-05 Smart Campus Energy Dashboard  
> **Repository:** `nguyenthetai0012/SE2026---T06`  
> **Mục đích:** Định hướng cho các AI Agents (Jules, Gemini Code Assist Agent Mode, ChatGPT, Claude, Cursor...) hoạt động đúng phạm vi, an toàn và tuân thủ quy trình làm việc của nhóm.

---

## 1. Tổng quan Dự án & Phân công Vai trò

Hệ thống **Smart Campus Energy Dashboard** nhận dữ liệu cảm biến mô phỏng qua giao thức **MQTT** từ nhiều tòa nhà trong khuôn viên trường học, lưu trữ và truy vấn chuỗi thời gian, quản lý danh mục thiết bị, hiển thị dashboard, cảnh báo bất thường và phát hiện thiết bị offline.

### 👥 Phân công nhiệm vụ các thành viên:
* **Tài (Backend/API):** Device registry, API endpoints, nhận/kiểm tra dữ liệu, truy vấn lịch sử, cảnh báo và offline status.
* **Sương (Dashboard):** Giao diện UI/UX theo từng màn hình, hiển thị trạng thái loading/empty/error/offline, lịch sử tiêu thụ và cảnh báo.
* **An (Simulator/Data):** Bộ giả lập sinh dữ liệu MQTT cho nhiều tòa nhà/thiết bị, quản lý schema, timestamp, nhịp gửi, xử lý dữ liệu lỗi/trùng/đến trễ/sai thứ tự.
* **Ngọc (QA/Security/DevOps):** Chiến lược kiểm thử (integration, e2e, load), kiểm tra dữ liệu sai/bảo mật, secret/dependency audit, cấu hình CI workflow với GitHub Actions.

---

## 2. Cấu trúc Thư mục Quy chuẩn (Project Structure)

Mọi thay đổi code hoặc tài liệu do Agent thực hiện PHẢI tuân thủ chính xác cấu trúc thư mục sau:

```text
SE2026---T06/
├── .github/                  # Workflows CI/CD & Issue Templates
│   ├── ISSUE_TEMPLATE/
│   └── workflows/            # GitHub Actions (Lint, Test, Review...)
├── docs/                     # Tài liệu hệ thống & quyết định thiết kế
│   ├── requirements/         # Yêu cầu màn hình/tính năng & tiêu chí nghiệm thu (AC)
│   ├── architecture/         # Mô tả kiến trúc hệ thống
│   ├── tasks/                # Lộ trình & phân chia công việc
│   ├── contracts/            # Quy ước API / MQTT Contract (Bắt buộc tuân thủ)
│   ├── testing/              # Chiến lược & kịch bản kiểm thử
│   └── decisions/            # Ghi nhận các quyết định kiến trúc (ADR)
├── src/                      # Mã nguồn ứng dụng
│   ├── backend/              # Mã nguồn Backend API & MQTT Consumer
│   ├── frontend/             # Mã nguồn Dashboard UI
│   └── simulator/            # Bộ giả lập cảm biến MQTT
├── tests/                    # Mã nguồn các bộ kiểm thử
│   ├── integration/          # Integration tests
│   ├── e2e/                  # End-to-end tests
│   └── load/                 # Performance & Load tests
├── tools/scripts/            # Kịch bản bổ trợ phát triển/vận hành
├── infrastructure/docker/    # Dockerfile, docker-compose cấu hình môi trường
├── README.md                 # Hướng dẫn tổng quan dự án
└── AGENTS.md                 # Quy tắc dành cho AI Agent (Tệp này)
```

⚠️ **DANH MỤC CẤM COMMIT:**
* **KHÔNG COMMIT** các thư mục/file sinh ra trong quá trình build/chạy ứng dụng: `build/`, `dist/`, `node_modules/`, `coverage/`, `.env`, file log, hoặc cache của hệ thống.

---

## 3. Quy trình Làm việc Bắt buộc của AI Agent (Workflow)

Mọi Agent khi thực hiện tác vụ liên quan đến Issue phải tuân thủ nghiêm ngặt 8 bước sau:

### Bước 1: Tiếp nhận & Phân tích Ngữ cảnh
* Đọc kỹ `AGENTS.md`, `README.md`, thông tin Issue được giao (`#ISSUE_NUMBER`) và các tài liệu liên quan trong thư mục `docs/`.
* Tóm tắt lại:
  1. Tiêu chí nghiệm thu (**AC - Acceptance Criteria**).
  2. Sự phụ thuộc contract với công việc của các thành viên khác.
  3. Đề xuất **Kế hoạch triển khai & danh sách tệp dự kiến sửa/tạo mới**.
* **CHỜ NGƯỜI PHỤ TRÁCH DUYỆT KẾ HOẠCH** trước khi tiến hành chỉnh sửa mã nguồn.

### Bước 2: Quản lý Nhánh (Branching)
* **TUYỆT ĐỐI KHÔNG** commit hoặc chỉnh sửa trực tiếp trên nhánh `main`.
* Mọi thay đổi phải thực hiện trên feature branch riêng với cú pháp:
  `feature/issue-ISSUE_NUMBER-mo-ta-ngan` (Ví dụ: `feature/issue-4-dashboard-requirements`).

### Bước 3: Ranh giới Tác động (Scope Control)
* Chỉ chỉnh sửa các tệp nằm trong phạm vi của Issue.
* Không tự ý thay đổi API/MQTT Contracts trong `docs/contracts/` khi chưa được nhóm thảo luận và chốt thống nhất.
* Không tự ý thêm thư viện ngoài (dependencies) hay thay đổi stack công nghệ đã chốt.
* Cập nhật các tệp kiểm thử tương ứng trong `tests/` và tài liệu trong `docs/` khi thay đổi logic.

### Bước 4: An toàn & Bảo mật (Security)
* **TUYỆT ĐỐI KHÔNG** đưa thông tin nhạy cảm vào mã nguồn hoặc log: API keys, passwords, tokens, secrets, thông tin cá nhân.
* Đọc cấu hình bí mật qua biến môi trường (Environment Variables).

### Bước 5: Kiểm tra Diff & Chạy Test
* Tiến hành kiểm tra và chạy thử các bộ test phù hợp với phạm vi vừa sửa.
* Sau khi hoàn thành, báo cáo rõ cho người phụ trách:
  1. Danh sách các tệp đã chỉnh sửa (`Files changed`).
  2. Mức độ đáp ứng từng tiêu chí nghiệm thu (AC).
  3. Câu lệnh kiểm thử đã chạy và kết quả thực tế.

### Bước 6: Đẩy Nhánh & Mở Pull Request (PR)
* Đẩy (publish/push) feature branch lên GitHub.
* Tạo Pull Request trỏ vào nhánh `main` kèm mô tả chi tiết.
* Liên kết PR với Issue:
  * Sử dụng `Closes #ISSUE_NUMBER` nếu PR hoàn tất trọn vẹn Issue.
  * Sử dụng `Refs #ISSUE_NUMBER` nếu PR mới chỉ giải quyết một phần.
* **KHÔNG TỰ MERGE** Pull Request. Việc merge thuộc quyền hạn của trưởng nhóm hoặc người duyệt (Reviewer).

---

## 4. Quy ước kỹ thuật và dữ liệu

- README và các contract/ADR đã được nhóm duyệt là nguồn quyết định kỹ thuật hiện hành. Nội dung được đánh dấu **đề xuất**, **bản nháp** hoặc **còn mở** không phải quy tắc bắt buộc.
- Ví dụ ISO-8601 UTC, metric `power_kw`/`energy_kwh`, đơn vị kW/kWh trong tài liệu hiện tại chỉ là ví dụ/đề xuất cho đến khi nhóm phê duyệt contract tương ứng.
- Khi nhóm đã duyệt quy ước thời gian, đơn vị và định danh trong contract, mọi thành phần phải tuân thủ cùng một quy ước; không tự thêm quy ước mới.
- Khi triển khai, phải tính đến các trường hợp được xác nhận trong yêu cầu và contract: dữ liệu trùng, đến trễ, sai thứ tự và thiết bị offline. Chính sách cụ thể phải lấy từ quyết định đã duyệt, không tự suy diễn từ ví dụ.

