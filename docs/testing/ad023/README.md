# AD-023 — Bằng chứng refactoring cho Dashboard query path

**Tác giả:** Tài (nguyenthetai0012), có hỗ trợ AI (Claude, ghi trong trailer commit).
**Phạm vi:** bài tập cá nhân. Đây **không** phải implementation đã được nhóm duyệt; stack Python ở đây đi theo **đề xuất** tại PR #23 (Issue #20), vẫn đang ở trạng thái draft. Nhánh: `feature/ad023-dashboard-refactoring-evidence`, không mở PR vào `main`.

## 1. Chuỗi commit

| Bước | Commit | Loại | Nội dung |
| --- | --- | --- | --- |
| C1 | `4662872` | baseline | Code ban đầu có 3 vấn đề cố ý + 14 characterization test |
| C2 | `9444acd` | refactor thuần | Tách `EnergyQueryPort`; SQL về Ingestion; gom logic tổng hợp. **Không sửa file test nào** |
| C3 | `76f7104` | fitness test | Luật kiến trúc R1–R4: 4 vi phạm trên C1, 0 trên C2 |
| C4 | `0f46e2a` | sửa lỗi (đổi hành vi có chủ đích) | Phân quyền theo tòa nhà (BOLA), bỏ payload thô, audit; +10 test bảo mật |
| C5 | `f197a0e` | evidence | Script benchmark, kết quả đo |
| C6 | `727114d` | tính năng (biến cố AD-023) | Batch theo phân vùng: cô lập lỗi, đối soát, khôi phục từng phần, giới hạn 49 ngày; luật R3/R5 |
| C7a | `f706376` | test trước khi sửa | Chốt biên cờ `late` (300 s / 301 s / qua nửa đêm) |
| C7 | `b569723` | refactor hiệu năng (giữ hành vi) | `strptime` → `fromisoformat`; không sửa file test |
| C8 | commit chứa file này | evidence | Đo tải 302 tác vụ đồng thời, cập nhật tài liệu |

Kiểm tra "C2 không sửa test": `git diff --stat 4662872 9444acd -- tests` → rỗng.

## 2. Ba vấn đề được phân tích

| Mã | Vấn đề | Loại | File ở C1 | Xử lý |
| --- | --- | --- | --- | --- |
| P1 | Dashboard và Reporting đọc thẳng bảng `sensor_readings` của Ingestion bằng SQL | Vi phạm ranh giới / data ownership; phụ thuộc sai chiều | `dashboard/service.py`, `reporting/daily_rollup.py` | C2: `core/ports.py` + `ingestion/energy_query.py` (DIP) |
| P2 | SQL tổng hợp năng lượng, luật cửa sổ `[start, end)`, làm tròn và bảng đơn vị bị lặp ở hai nơi | **Code smell: Duplicated Code** (kéo theo Shotgun Surgery khi đổi schema) | như trên + `ingestion/store.py` (UNITS) | C2: một adapter, một `round_kwh`, một `UNITS` |
| P3 | Không kiểm tra quyền; trả `raw_debug_records` (payload thô) cho người gọi | Bảo mật: BOLA + lộ dữ liệu | `dashboard/service.py` | C4: `core/auth.py`, kiểm tra quyền mọi truy vấn |

Bất biến được giữ qua refactor (test `test_rollup_agrees_with_dashboard_for_the_same_day`): tổng ngày của Rollup bằng tổng quan Dashboard cùng ngày.

## 3. Cách chạy lại

Từ thư mục gốc repo, Python ≥ 3.10, không cần cài thêm thư viện:

```bash
python -m unittest discover -s tests/ad023 -t . -v     # 26 test
python -m tests.ad023.test_architecture                # luật R1–R4
python tools/scripts/ad023_bench.py --out /tmp/b.json  # benchmark (~6 s seed)
python tools/scripts/ad023_load.py --pool 4            # 302 tác vụ đồng thời (~15 s/lần)
```

Chạy luật kiến trúc trên baseline:

```bash
git worktree add /tmp/c1 4662872
AD023_SRC=/tmp/c1/src/backend/ad023 python -m tests.ad023.test_architecture
```

## 4. Kết quả đã ghi

**Test** (Python 3.13.17, 25/10/2026): C1 14/14, C2 14/14 (cùng file test), C3 16/16, C4 26/26, C6 38/38, C7 39/39.

**Luật kiến trúc:** [`results/architecture-c1-vs-c2.txt`](results/architecture-c1-vs-c2.txt).

**Benchmark** ([`bench-c1.json`](results/bench-c1.json), [`bench-c2.json`](results/bench-c2.json), [`bench-c4.json`](results/bench-c4.json)). Bộ dữ liệu: 10 tòa nhà, 100 thiết bị, 30 ngày, 15 phút/lần = 288.000 reading; 500 lời gọi mỗi thao tác, 3 lần lặp; SQLite in-memory, 2 vCPU.

| Thao tác (cửa sổ 24h) | C1 p95 (ms) | C2 p95 (ms) | C4 p95 (ms) |
| --- | --- | --- | --- |
| Tổng quan tòa nhà | 19.2 – 23.9 | 24.2 – 25.0 | 0.42 – 0.56 |
| Lịch sử thiết bị | 1.07 – 1.35 | 1.02 – 1.60 | 1.15 – 1.31 |

Diễn giải:
- **C1 → C2 không đổi hiệu năng** (nằm trong dao động giữa các lần chạy). Refactor qua port không thêm chi phí đáng kể, nhưng cũng không làm nhanh hơn.
- **C4 nhanh hơn khoảng 40 lần ở tổng quan** vì đã bỏ truy vấn `raw_debug_records` (sắp xếp toàn bộ reading của tòa nhà theo `received_at`, không có index). Lợi ích này đến từ việc sửa P3, **không** đến từ refactor.

**Biến cố batch (C6)** — `tests/ad023/test_batch_recovery.py`: bản phát hành lỗi làm sai im lặng BLD-B (×1000) và làm sập BLD-C. BLD-A vẫn publish đúng; BLD-C bị cách ly, giữ giá trị tốt cũ; `reconcile` trả `["BLD-B","BLD-C"]`; `recover` chỉ tính lại hai phân vùng đó (spy xác nhận BLD-A không bị tính lại, `run_id` giữ nguyên); quá 49 ngày thì từ chối khôi phục.

**Tải 302 tác vụ đồng thời** (`tools/scripts/ad023_load.py`, mỗi tác vụ 1 luồng + 1 kết nối, quyền 1 tòa nhà; 9 request hợp lệ + 1 lần thử tòa nhà khác; batch lỗi BLD-03 chạy song song rồi được khôi phục; 3 lần chạy/cấu hình, 3.020 request/lần):

| Cấu hình | Code | p95 | Đạt ≤ 1,5 s? | File |
| --- | --- | --- | --- | --- |
| Burst, không giới hạn kết nối | C7 | 2,40–2,50 s | Không | `load-burst-unbounded.json` |
| Burst, không giới hạn, **không có batch** | C7 | 2,45–2,60 s | Không | `load-burst-unbounded-nobatch.json` |
| Burst, pool 4 kết nối | C6 | 1,36–1,42 s | Sát ngưỡng | `load-burst-pool4-c6.json` |
| Burst, pool 4 kết nối | C7 | 0,68–0,74 s | Có | `load-burst-pool4.json` |
| Ổn định, think time TB 1 s, không giới hạn | C7 | 1,1–1,5 ms | Có | `load-steady-unbounded.json` |
| Ổn định, think time TB 1 s, pool 4 | C7 | 1,1–2,0 ms | Có | `load-steady-pool4.json` |

Ở **mọi** lần chạy: 302/302 lần truy cập trái phép bị từ chối, 0 lần lộ dữ liệu, 0 lỗi khác; batch phát hiện 30/300 phân vùng sai, khôi phục 30, còn 0 sai sau khôi phục (chỉ tính lại 10% số phân vùng).

Tắt batch không làm p95 burst tốt hơn → batch không phải nguyên nhân; nguyên nhân là 302 kết nối tranh chấp 2 vCPU (và trước C7, `strptime` tốn 1,39 ms/response lịch sử).

Kết luận: mục tiêu p95 ≤ 1,5 s chỉ đạt khi **giới hạn số truy vấn đồng thời** (pool) hoặc tải có think time; burst không giới hạn trên 2 vCPU vượt mục tiêu. Đây là evidence trigger trong ADR của bài.

## 5. Giới hạn — không dùng các số này cho

- p95 của API/HTTP, MQTT, nhiều người dùng đồng thời hoặc PostgreSQL: chưa đo.
- Xác thực (token/session) vẫn **[CÒN MỞ]** trong nhóm; `Principal` ở đây giả định đã xác thực.
- `energy_kwh` được coi là điện năng theo từng khoảng (cộng dồn). Đây là giả định của bài, Q1 trong `backend-api.md` vẫn **[CÒN MỞ]** chờ An xác nhận.
- `LATE_AFTER_SECONDS = 300` lấy từ đề xuất MQTT PR #10, chưa duyệt.
