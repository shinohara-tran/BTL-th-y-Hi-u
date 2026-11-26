# Phần 2 trên bộ dữ liệu chung team_docs_final

Đo ngày 25/11/2026 bằng Qdrant server (Docker, image `v1.14.0`), trên 14.022 chunk của 13 công ty. Đây là bộ dữ liệu cuối của nhóm, đã gồm cách chia đoạn mới của Phần 1. Chấm bằng benchmark gốc: 25 câu hỏi, k = 10.

## Các cấu hình

| Mã | Code | Ngăn (collection) | Ý nghĩa |
|---|---|---|---|
| F0 | `main` | `team_docs_final_idf` | Mốc so sánh: SPLADE bật lại IDF, BM25 dùng `embed()` cho câu hỏi |
| F1 | `part-2` | `team_docs_final_idf` | F0 + câu hỏi BM25 dùng `query_embed()` |
| F2 | `part-2` | `team_docs_final` | F1 + SPLADE bỏ IDF. Đây là bộ nhóm phát hành |
| F3 | `part-2` | `team_docs_final_e3` | F2 + Dense `bge-base-en-v1.5` (768 chiều) |

Ngăn `team_docs_final_idf` được tạo bằng cách chép vector của `team_docs_final` sang, dùng code `main` (`scripts/team/clone_collection.py`, chạy khoảng 1 phút). Ngăn `team_docs_final_e3` thì phải tạo lại vector Dense, mất 70 phút.

## Kết quả

MRR:

| | BM25 | Dense | BM25+Dense | SPLADE | SPLADE+Dense | Rerank |
|---|---|---|---|---|---|---|
| F0 | 0,893 | 0,800 | 0,846 | 0,840 | 0,840 | 0,833 |
| F1 | 0,893 | 0,800 | 0,846 | 0,840 | 0,840 | 0,833 |
| F2 | 0,893 | 0,800 | 0,866 | **0,860** | **0,853** | **0,853** |
| F3 | 0,893 | **0,824** | 0,866 | 0,860 | 0,853 | 0,853 |

NDCG@10:

| | BM25 | Dense | BM25+Dense | SPLADE | SPLADE+Dense | Rerank |
|---|---|---|---|---|---|---|
| F0 | 0,895 | 0,853 | 0,876 | 0,884 | 0,874 | 0,900 |
| F1 | 0,895 | 0,853 | 0,875 | 0,884 | 0,874 | 0,900 |
| F2 | 0,895 | 0,853 | 0,879 | **0,895** | 0,874 | 0,903 |
| F3 | 0,895 | 0,854 | 0,878 | 0,895 | 0,876 | 0,901 |

Độ trễ trung vị (p50) của Dense: F2 là 57 ms, F3 là 125 ms.

## Kết luận

1. **Bỏ IDF cho SPLADE là cải tiến duy nhất có tác dụng ổn định.** Trên bộ final, MRR tăng 0,02 ở SPLADE, SPLADE+Dense và Rerank; NDCG@10 của SPLADE tăng từ 0,884 lên 0,895. Lần này nhóm câu khái niệm (Semantic) cũng tăng, từ 0,557 lên 0,589. Ở các bộ dữ liệu cũ, nhóm này lại giảm.
2. **Câu hỏi BM25 dùng `query_embed()` không làm thay đổi kết quả.** Điều này lặp lại trên cả 3 bộ dữ liệu. Code cũ nhân mọi từ trong câu hỏi với cùng một hệ số, nên thứ hạng không đổi. Sửa là để code đúng lý thuyết, không phải để tăng điểm.
3. **bge-base giúp Dense nhưng không giúp hệ thống.** MRR của Dense tăng từ 0,800 lên 0,824, Recall@10 từ 0,84 lên 0,88. Tuy vậy, các cách tìm kết hợp gần như giữ nguyên, nhóm Semantic còn giảm (0,510 xuống 0,490), độ trễ Dense tăng gấp đôi, và phải mất 70 phút tạo lại vector. **Giữ bge-small làm mặc định.**
4. **Ghi chú cho Phần 1.** Nhờ cách chia đoạn mới, Dense hiểu câu khái niệm tốt hơn hẳn: NDCG nhóm Semantic từ 0,39 (bộ cũ 13.137 chunk) lên 0,51. Đổi lại, MRR của BM25 giảm từ 0,928 xuống 0,893.

## Lỗi Dense bằng 0 ở bộ team13-fy (tự đo)

Bản `team13-fy` lưu **toàn bộ 13.137 vector Dense là vector 0**. Đo bằng benchmark gốc, code `main`:

| Bản | Vector Dense bằng 0 | MRR Dense | Recall@10 Dense | MRR BM25+Dense | MRR SPLADE+Dense |
|---|---|---|---|---|---|
| team13-fy | 13.137 / 13.137 | **0,211** | 0,44 | 0,664 | 0,738 |
| team13-densefix | 0 / 13.137 | **0,827** | 0,92 | 0,920 | 0,847 |

Dense "sụp" vì dữ liệu bị lưu hỏng, không phải vì mô hình yếu. Sau khi sửa, MRR 0,827 khớp đúng với số đo trên bộ 10 công ty của repo gốc. Vector hỏng kéo luôn các cách tìm kết hợp có Dense đi xuống. Kết quả chi tiết của bản densefix (E0–E2) nằm ở `../team13/`; file `E0_densezero_team13fy.md` là phép đo trên bản hỏng.

## Giới hạn

- Chỉ có 25 câu hỏi; chênh lệch MRR khoảng 0,02 tương ứng 1 câu đổi thứ hạng.
- Chỉ mục HNSW của Dense là tìm gần đúng và được dựng riêng cho từng ngăn. Vì vậy cột BM25+Dense lệch 0,02 giữa F1 và F2, dù hai cấu hình này không khác nhau ở BM25 hay Dense. Chênh lệch dưới 0,02 nên coi là nhiễu.
- Benchmark gốc chấm bằng từ khóa, thiên vị BM25. `evaluate.py --tag part2` đã chạy trên `team_docs_final` (`evaluation/team/results/part2.md`), nhưng nhóm chưa có nhãn chấm tay, nên chỉ có `company@5`, `dup@5` và độ trễ.

## Chạy lại

```
bash docs/team/part2/final/run_final.sh
```

Chạy từ thư mục gốc của repo, khi Docker đang chạy `team_docs_final`. Cần thêm bản `main` ở `../BTL-main`, tạo bằng `git worktree add ../BTL-main origin/main`.
