# Kết quả đánh giá

Số chính thức của nhóm là **`team.md`** (và `team.json`). Bản này chạy 24 câu với 603 nhãn trên collection `team_docs_final` (14.022 chunk), ngày 26/11/2026.

| File | Dùng cho | Ghi chú |
|---|---|---|
| `team.md`, `team.json` | Kết quả cuối, slide, README, tab Benchmark của web demo | Chính thức |
| `baseline.*`, `baseline_part1.*`, `part1.*`, `part2.*`, `compare.md` | So sánh trước và sau Phần 1, Phần 2 | Chạy trước khi có nhãn, nên chỉ có company@5, dup@5 và độ trễ. `baseline*` chạy trên `team_docs` (13.137 chunk), bộ có vector Dense bằng 0 |
| `rerank_batches.json` | Phần 4: độ trễ cross-encoder theo batch size | |
| `part4_final_demo.json` | Phần 4: các câu demo trích số | |
| `archive/` | Kết quả cũ trên dữ liệu lỗi | Không dùng, xem `archive/README.md` |
