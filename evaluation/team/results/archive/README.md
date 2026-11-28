# Kết quả cũ, không dùng

Các file trong thư mục này được đo ngày 24/11/2026 trên bộ dữ liệu trung gian (collection `team_docs`, 13.137 chunk). Bộ đó có toàn bộ vector Dense bằng 0, nên mọi số của Dense và các cấu hình có Dense đều sai (ví dụ Dense MRR 0,385 trên benchmark của tác giả).

Phần đầu các file `benchmark_*.md` ghi "8,609 chunks, 10 companies". Đó là câu mẫu của báo cáo gốc, không phải dữ liệu thật của lần chạy.

Nhóm giữ lại để thấy quá trình làm và lỗi đã phát hiện. Số chính thức nằm ở [`../team.md`](../team.md).

| File | Nội dung |
|---|---|
| `benchmark_baseline_13cty.md` | Benchmark của tác giả, 6 cấu hình gốc, 13 công ty |
| `benchmark_part3_13cty.md` | Như trên, thêm 3 cấu hình Phần 3 (trọng số cũ 0,3/0,7) |
| `benchmark_part3_w05.md` | Như trên, trọng số 0,5 |
| `part3.*`, `part3-w05.*`, `part3-code08.*` | Bộ 24 câu của nhóm, chạy trước khi có nhãn |
