# Phần 2 – minh chứng thử nghiệm

Các sửa đổi code nằm ở 3 commit trên nhánh `part-2`:

| Commit | Nội dung |
|---|---|
| `fix(bm25)` | Câu hỏi BM25 dùng `query_embed()` (E1) |
| `fix(splade)` | Bỏ `Modifier.IDF` cho vector SPLADE (E2) |
| `feat(part2)` | Biến `DENSE_MODEL`, `DENSE_VECTOR_SIZE` và `scripts/team/clone_collection.py` (dùng cho E2, E3) |

Xem diff: `git log -p main..part-2 -- src scripts`

**Số liệu chính để đưa vào báo cáo chung: `final/KET_QUA.md`.** Phần này đo trên bộ dữ liệu cuối `team_docs_final` (14.022 chunk, 13 công ty, Qdrant chạy trong Docker), gồm các cấu hình F0–F3 và kết quả `evaluate.py --tag part2`.

Các thư mục khác:

| Thư mục | Dữ liệu | Ghi chú |
|---|---|---|
| `final/` | `team_docs_final`, 14.022 chunk | **Bản chính** |
| `team13/` | `team_docs` bản densefix, 13.137 chunk | E0–E2, cộng phép đo trên bản `team13-fy` có vector Dense bằng 0 |
| `1_bao_cao/`, `2_log/` | Repo gốc, 10 công ty, 8.670 chunk, Qdrant embedded | E0–E3 làm lần đầu. Không so sánh được với số của cả nhóm |

Mục lục và bảng so sánh cả 3 bộ (trước và sau khi sửa Phần 1): `00_MUC_LUC.md`.
