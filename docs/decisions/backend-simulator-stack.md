# ADR: Stack Backend, MQTT broker, lưu trữ và Simulator

- Issue: [#20 — Chốt stack Backend, MQTT broker, lưu trữ và Simulator](https://github.com/nguyenthetai0012/SE2026---T06/issues/20)
- Phụ trách: Tài (Backend/lưu trữ); An (Simulator/MQTT); Ngọc (CI/môi trường); Sương đối chiếu tích hợp Frontend (#11)
- Trạng thái: **[ĐỀ XUẤT]** — chưa được nhóm duyệt; không mặc định Node/Python hay một DB/broker là bắt buộc
- Không thuộc issue này: API schema (#21), ngưỡng cảnh báo, mục tiêu hiệu năng, RE-022, lệnh chạy đã kiểm chứng

Frontend stack ghi ở ADR Issue #11 / [PR #17](https://github.com/nguyenthetai0012/SE2026---T06/pull/17); tài liệu này **không** quyết định lại UI.

---

## 1. Nhu cầu kỹ thuật (từ yêu cầu đã có)

Phải chạy được cục bộ: Simulator → MQTT → Backend intake → lưu readings/registry/cảnh báo/offline → API cho Dashboard. Phải kiểm thử được ingestion, trùng, trễ, sai thứ tự, rỗng vs lỗi (kế hoạch #5).

---

## 2. Phương án đã cân nhắc

### 2.1 Runtime Backend

| Phương án | Ưu | Nhược |
| --- | --- | --- |
| **A. Python 3.12 + FastAPI + Uvicorn** | MQTT (`paho-mqtt`) phổ biến; pytest; sau này dễ xuất OpenAPI cho #21 | Khác ngôn ngữ với Frontend React (nếu #11 chọn vậy) |
| **B. Node.js 20 LTS + Fastify hoặc Express** | Cùng hệ sinh thái JS/TS với Frontend đề xuất | MQTT/time-series tooling ít “mặc định” hơn Python trong nhiều giáo trình IoT |

**[ĐỀ XUẤT] A — Python 3.12 + FastAPI.** Lý do: intake MQTT + validation + test fixture (#3/#5) gọn; không phụ thuộc quyết định UI. **[CÒN MỞ]** nếu nhóm ưu tiên một ngôn ngữ với Frontend → chuyển B.

Phiên bản dự kiến (chưa cài, chưa kiểm chứng): Python 3.12.x, FastAPI 0.115+, Uvicorn. Dependency: `pyproject.toml` / `requirements.txt` khi tạo khung.

### 2.2 MQTT broker và client

| Phương án | Ưu | Nhược |
| --- | --- | --- |
| **A. Eclipse Mosquitto 2.x** | Nhẹ, chạy local, tài liệu nhiều, miễn phí | Cần cài binary hoặc container |
| **B. EMQX** | Nhiều tính năng | Nặng hơn nhu cầu MVP môn học |
| **C. Broker nhúng trong process** | Ít bước cài | Khác môi trường demo thật, khó tách Simulator/Backend |

**[ĐỀ XUẤT] A — Mosquitto 2.x** trên máy local; Docker là **tuỳ chọn** (Issue #22 không bắt buộc Docker). Client: `paho-mqtt` phía Backend và Simulator nếu chọn Python.

**[CÒN MỞ]** topic MQTT chính thức (không chốt trong ADR này; thuộc #3).

### 2.3 Lưu trữ

| Phương án | Ưu | Nhược |
| --- | --- | --- |
| **A. PostgreSQL 16** | Registry + readings + alerts một DB; truy vấn theo thời gian đủ cho MVP; test được | Không phải TSDB chuyên dụng |
| **B. SQLite** | Không cần service | Yếu khi load test / nhiều writer MQTT |
| **C. InfluxDB / Timescale** | Đúng time-series | Thêm vận hành; dư cho MVP nếu chưa có yêu cầu tải đã chốt |

**[ĐỀ XUẤT] A — PostgreSQL 16** cho registry, readings (`event_time`, `received_at`), alerts, last-seen. **[CÒN MỞ]** Timescale sau nếu #5 yêu cầu tải vượt PostgreSQL thường.

ORM/driver dự kiến (chưa kiểm chứng): SQLAlchemy 2.x + psycopg. Cấu hình qua biến môi trường, không commit mật khẩu.

### 2.4 Simulator

| Phương án | Ưu | Nhược |
| --- | --- | --- |
| **A. Python 3.12 + paho-mqtt** | Cùng ngôn ngữ Backend đề xuất; dễ fixture lỗi/trễ/trùng | An phải đồng ý runtime |
| **B. Node.js** | Nếu An đã quen JS | Hai runtime MQTT nếu Backend là Python |

**[ĐỀ XUẤT] A**, khớp Backend đề xuất. **An xác nhận** trước khi coi là đã duyệt.

---

## 3. Tổ hợp đề xuất (chờ xác nhận)

| Thành phần | Lựa chọn đề xuất | Phiên bản dự kiến | Điều kiện môi trường |
| --- | --- | --- | --- |
| Backend | FastAPI trên Python | 3.12 | Windows/macOS/Linux local; venv |
| MQTT broker | Eclipse Mosquitto | 2.x | Cổng 1883 local; không TLS bắt buộc ở MVP |
| MQTT client | paho-mqtt | 2.x | Dùng cho Backend consumer và Simulator |
| Lưu trữ | PostgreSQL | 16 | Service local hoặc container tuỳ chọn |
| Simulator | Python + paho-mqtt | 3.12 | Cùng major Python với Backend |

Đây **không** phải lệnh đã chạy thành công. Cấm tuyên bố “cài đặt đã kiểm chứng” cho đến khi có bằng chứng trên Issue #22 / PR tạo khung.

---

## 4. Tương thích và CI

- **Tài / An:** cùng Python giúp chia schema test; nếu An giữ Node, ADR phải ghi hai runtime và Ngọc bổ sung CI.
- **Ngọc:** CI (sau khi stack duyệt) lint/test Python, không giả định Docker; secret chỉ qua env.
- **Sương:** Backend đề xuất HTTP JSON đồng bộ cho MVP; realtime **[CÒN MỞ]** như #2/#21.

---

## 5. Checklist duyệt

- [ ] Tài xác nhận Backend + PostgreSQL + Mosquitto phù hợp năng lực nhóm
- [ ] An xác nhận runtime Simulator và client MQTT
- [ ] Ngọc rà soát chạy local / CI / cấu hình không secret
- [ ] Sương: không xung đột hướng tích hợp #11
- [ ] Cập nhật liên kết README **sau khi merge** ADR (không sửa main trực tiếp)

Khi đủ tick, chuyển trạng thái tài liệu sang **[ĐÃ XÁC NHẬN]** trên PR, rồi mới giao việc tạo khung `src/backend/` và `src/simulator/`.
