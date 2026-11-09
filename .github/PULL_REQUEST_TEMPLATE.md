## Vấn đề và hành vi sau thay đổi

Refs #... (chỉ dùng Closes #... khi hoàn tất toàn bộ Issue).

## Phạm vi và ảnh hưởng

- File/module chính:
- API/MQTT/schema/producer/consumer bị ảnh hưởng:
- Quyết định hoặc phụ thuộc còn mở:

## Kiểm chứng thực tế

| Lệnh / test | Môi trường / seed | Expected / actual | PASS / FAIL / CHƯA CHẠY |
| --- | --- | --- | --- |
| | | | |

Liên kết bằng chứng đã loại secrets; nêu rõ mock hay tích hợp thật.

## Checklist

- [ ] Nhánh riêng đúng quy tắc; phạm vi khớp Issue.
- [ ] Contract thay đổi được producer/consumer review.
- [ ] Có test phù hợp, báo đúng kết quả; các checks bắt buộc đạt.
- [ ] Tài liệu được cập nhật; hạn chế/rủi ro còn lại được ghi rõ.
- [ ] Không có secrets, `.env`, log hoặc output build trong diff.
- [ ] Có reviewer khác; tác giả/agent không tự merge.
