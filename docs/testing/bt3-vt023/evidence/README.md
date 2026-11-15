# Log thực thi BT3 VT-023 (đầu ra nguyên văn của các lệnh đã chạy)

Máy chạy: Linux 2 vCPU, Python 3.12.3, PostgreSQL 16.15. Lệnh chạy lại nằm ở `../README.md`.

| File | Nội dung | Commit |
| --- | --- | --- |
| `00_baseline_tests.txt` | Suite trên baseline: 76 passed | `63ed1b9` |
| `01_red_tests_only.txt` | RED 1: chỉ có test, chưa có schema hay code | `1983729` |
| `02_red_schema_only.txt` | RED 2: có schema, chưa có route; 12 test pass (7 pass rỗng); RED 2b sau khi siết test | `d71df1b`, `36605a2` |
| `03_green.txt` | GREEN lần đầu: 124 passed | `afc1c9f` |
| `04_mutation.txt`, `04_mutation_final.txt` | Mutation M1–M4 (lần đầu, và chạy lại sau perf) | `afc1c9f`, `a3fdb73` |
| `05_coverage.txt`, `06_flaky.txt` | Coverage, thứ tự ngẫu nhiên, TZ, lặp TC11 | `2ea64ee` |
| `07_load.txt`, `07b_profile.txt` | Tải trước khi sửa (p95 ≈ 12 s) và profile CPU | `afc1c9f` |
| `08_load_after.txt` | Tải sau khi đổi sang đọc cột bằng Core | `a3fdb73` |
| `patch_for_review.diff` | Diff đưa cho AI reviewer | `63ed1b9..2ea64ee` |
| `09`–`12`, `17` | Kiểm chứng nhận xét AI review: M5/M6 sống sót, REPEATABLE READ trả 503, số liệu replay, test đỏ trước khi sửa, `compare_metadata` bỏ qua CHECK | `a3fdb73`/`2ea64ee` |
| `13_mutation_final.txt` | Mutation cuối: 6/6 KILLED | `a2f06cf` |
| `14_load_final.txt` | Tải cuối, 1 và 2 worker | `a2f06cf` |
| `15_green_final.txt`, `16_final_cov_flaky.txt` | GREEN cuối 129 passed, coverage và flaky | `e1a0ca0` |

Không có token thật trong các log này. Chuỗi `AAAA…` là token giả của rule C2.
