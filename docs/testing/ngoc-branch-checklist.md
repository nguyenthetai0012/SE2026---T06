# Checklist branch và bàn giao — Ngọc

- [ ] Issue ghi mục tiêu, AC, phạm vi, phụ thuộc và cách kiểm chứng.
- [ ] Kế hoạch thay đổi được người phụ trách duyệt theo AGENTS trước khi sửa mã nguồn.
- [ ] Làm trên `feature/issue-<số-issue>-<mô-tả>`, không sửa/commit trực tiếp `main`.
- [ ] Giữ một nhánh cho cùng task; kiểm tra `git status` và diff trước khi commit.
- [ ] Không thêm `.env`, secret, logs, cache, dependencies hoặc output build vào Git.
- [ ] Thay đổi contract có review của producer/consumer; ghi rõ quyết định còn chờ.
- [ ] Chạy kiểm tra phù hợp; phân biệt fixture check, infrastructure smoke và application integration.
- [ ] PR dùng template, liên kết Issue và ghi actual/expected, hạn chế và bằng chứng.
- [ ] Reviewer khác kiểm tra; required checks đạt trước khi merge; agent không tự merge.

Quản trị viên cần cấu hình ruleset/branch protection cho `main`: yêu cầu PR, reviewer và các checks được nhóm chọn. File này không tự bật cài đặt GitHub. Tên check chỉ đưa vào required checks sau khi workflow đã chạy thật trên GitHub.
