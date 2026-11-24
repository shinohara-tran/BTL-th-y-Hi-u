# Phần 2 – minh chứng thử nghiệm

Các sửa đổi code nằm ở 3 commit trên nhánh `part-2`:

| Commit | Nội dung |
|---|---|
| `fix(bm25)` | Câu hỏi BM25 dùng `query_embed()` (E1) |
| `fix(splade)` | Bỏ `Modifier.IDF` cho vector SPLADE (E2) |
| `feat(part2)` | Biến `DENSE_MODEL`, `DENSE_VECTOR_SIZE` và `scripts/team/clone_collection.py` (dùng cho E2, E3) |

Xem diff: `git log -p main..part-2 -- src scripts`

**Lưu ý:** E0–E3 chạy trên bộ dữ liệu của repo gốc (47 báo cáo, 10 công ty, 8.670 chunk), bằng benchmark gốc (`cli benchmark`, chấm theo từ khóa), chế độ Qdrant embedded. Chưa chạy lại trên bộ 13 công ty `team_docs` và chưa chấm bằng `scripts/team/evaluate.py`.

Bắt đầu đọc từ `00_MUC_LUC.md`.
