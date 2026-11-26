# Minh chứng Phần 2: Ba cách tạo vector (BM25, Dense, SPLADE)

Nhóm 3, Topic 3 Hybrid Search. Phần 2 được đo trên 3 bộ dữ liệu, chạy từ ngày 20 đến 25/11/2026, cùng một máy (i5-12450HX, 16 GB RAM, CPU).

## Ba bộ dữ liệu

| | Bộ gốc của tác giả | Trước khi sửa Phần 1 | Sau khi sửa Phần 1 |
|---|---|---|---|
| Số công ty | 10 | 13 | 13 |
| Số đoạn (chunk) | 8.670 | 13.137 | 14.022 |
| Độ dài trung vị | 478 token | 487 token | 454 token |
| Đoạn dài nhất | 892 token | 892 token | 480 token |
| Đoạn dài quá 512 token | 2.003 (23,1%) | 3.967 (30,2%) | 0 |
| Ngăn Qdrant | `financial_docs` | `team_docs` (bản densefix) | `team_docs_final` |
| Qdrant | embedded | server (Docker) | server (Docker) |
| Thử nghiệm | E0–E3 | E0–E2 | F0–F3 |
| Thư mục | `1_bao_cao/`, `2_log/` | `team13/` | `final/` |

Token được đếm bằng bộ tách token của bge-small, gồm cả dòng nhãn. Dense và SPLADE chỉ đọc 512 token đầu, nên trước khi sửa Phần 1, gần 1/3 số đoạn bị cắt đuôi trong hai vector này. BM25 không bị giới hạn. Sau khi sửa, cả 3 vector đều đọc trọn đoạn.

**Số liệu chính để đưa vào báo cáo chung là bộ sau khi sửa Phần 1: `final/KET_QUA.md`.** Hai bộ còn lại dùng để so sánh, không so trực tiếp được với số của cả nhóm.

## Các thử nghiệm

| Mã | Thay đổi | Code |
|---|---|---|
| E0 / F0 | Bản gốc: BM25 dùng `embed()` cho câu hỏi, SPLADE bật `Modifier.IDF` | `main` |
| E1 / F1 | E0 + câu hỏi BM25 dùng `query_embed()` | `part-2` |
| E2 / F2 | E1 + SPLADE bỏ `Modifier.IDF` | `part-2` |
| E3 / F3 | E2 + Dense `bge-base-en-v1.5` (768 chiều) | `part-2` |

Bộ trước khi sửa Phần 1 không chạy E3.

## Kết quả MRR (benchmark gốc, 25 câu hỏi, k = 10)

| Bộ | Mã | BM25 | Dense | BM25+Dense | SPLADE | SPLADE+Dense | Rerank |
|---|---|---|---|---|---|---|---|
| Gốc 10 công ty | E0 | 0,933 | 0,827 | 0,926 | 0,877 | 0,840 | 0,893 |
| | E1 | 0,933 | 0,827 | 0,926 | 0,877 | 0,840 | 0,893 |
| | E2 | 0,933 | 0,827 | 0,926 | **0,913** | **0,875** | **0,896** |
| | E3 | 0,933 | **0,831** | 0,908 | 0,913 | **0,890** | 0,895 |
| Trước sửa Phần 1 | E0 | 0,928 | 0,827 | 0,920 | 0,875 | 0,847 | 0,897 |
| | E1 | 0,928 | 0,827 | 0,900 | 0,875 | 0,847 | 0,897 |
| | E2 | 0,928 | 0,827 | 0,900 | **0,913** | **0,875** | 0,895 |
| Sau sửa Phần 1 | F0 | 0,893 | 0,800 | 0,846 | 0,840 | 0,840 | 0,833 |
| | F1 | 0,893 | 0,800 | 0,846 | 0,840 | 0,840 | 0,833 |
| | F2 | 0,893 | 0,800 | 0,866 | **0,860** | **0,853** | **0,853** |
| | F3 | 0,893 | **0,824** | 0,866 | 0,860 | 0,853 | 0,853 |

NDCG@10 của từng bộ nằm trong file báo cáo của thư mục tương ứng.

## Kết luận

1. **Bỏ IDF cho SPLADE (E2/F2) là cải tiến duy nhất có tác dụng trên cả 3 bộ.** MRR của SPLADE tăng 0,02 đến 0,04.
2. **Câu hỏi BM25 dùng `query_embed()` (E1/F1) không làm thay đổi thứ hạng của BM25.** Hàm cũ nhân mọi từ trong câu hỏi với cùng một hệ số, nên thứ tự không đổi. Sửa là để code đúng lý thuyết. Cột BM25+Dense có lúc lệch 0,02 là do chỉ mục HNSW tìm gần đúng, không phải do BM25.
3. **bge-base (E3/F3) giúp Dense nhưng không giúp hệ thống.** Dense tăng nhẹ, các cách kết hợp gần như giữ nguyên, trong khi độ trễ Dense tăng gấp đôi và phải tạo lại vector (45 đến 70 phút). Giữ bge-small.
4. **Sửa Phần 1 giúp Dense hiểu câu khái niệm tốt hơn.** NDCG@10 nhóm Semantic của Dense tăng từ 0,39 (trước sửa) lên 0,51 (sau sửa), vì đoạn văn không còn bị cắt đuôi. Đổi lại, MRR của BM25 giảm từ 0,928 xuống 0,893.
5. BM25 dùng một mình có MRR cao nhất ở cả 3 bộ.

## Lỗi dữ liệu Dense bằng 0

Bản `team13-fy` lưu toàn bộ 13.137 vector Dense là vector 0, khiến MRR của Dense chỉ còn 0,211. Bộ "trước khi sửa Phần 1" ở trên là bản đã sửa lỗi này (densefix), MRR Dense 0,827. Chi tiết: `team13/E0_densezero_team13fy.md` và `final/KET_QUA.md`.

## Giới hạn

- Chỉ có 25 câu hỏi. MRR chênh khoảng 0,02 tương ứng 1 câu đổi thứ hạng; chênh dưới 0,02 nên coi là nhiễu.
- Benchmark gốc chấm theo từ khóa có sẵn (`evaluation/benchmark.py`), nên thiên vị BM25 và đánh giá thấp Dense.
- Bộ gốc chạy trên Qdrant embedded, hai bộ sau chạy trên Qdrant server, nên độ trễ chỉ so được giữa các thử nghiệm trong cùng một bộ.

## Nội dung thư mục

| Thư mục | Nội dung |
|---|---|
| `final/` | Bộ sau khi sửa Phần 1: F0–F3, `KET_QUA.md`, log, `run_final.sh` |
| `team13/` | Bộ trước khi sửa Phần 1: E0–E2, phép đo trên bản Dense bằng 0, log, `run_all.sh` |
| `1_bao_cao/` | Bộ gốc: báo cáo E0–E3. Chỉ bảng 1 đến 3 là số đo; mục 5 đến 7 là chữ viết sẵn trong `report.py` |
| `2_log/` | Bộ gốc: output khi chạy. `e3_build.log` ghi tiến độ tạo vector Dense |
| `3_code/phan2_sua_doi.diff` | Các dòng code đã sửa so với commit gốc `16682dd` |
| `4_cau_hinh/` | Bộ gốc: cấu hình các ngăn (`qdrant_meta.json`) và thông tin máy |
| `5_bang_chung/ket_qua.txt` | Bộ gốc: kết quả tóm tắt |
| `5_chi_ra_loi_code_goc.md` | Giải thích các lỗi của code gốc ở Phần 2 |
| `scripts/team/clone_collection.py` | Script tạo ngăn mới bằng cách chép vector (nằm trong code) |

## Chạy lại

Bật Docker Desktop và container Qdrant trước khi chạy.

- Bộ sau khi sửa Phần 1: `bash docs/team/part2/final/run_final.sh`, chạy từ thư mục gốc repo. Cần bản `main` ở `../BTL-main` (`git worktree add ../BTL-main origin/main`).
- Bộ trước khi sửa Phần 1: `bash docs/team/part2/team13/run_all.sh`.
- Bộ gốc: chạy từ thư mục chứa `qdrant_data`:

```
set QDRANT_COLLECTION=financial_docs_e2
python -m hybrid_search.cli benchmark --k 10 --runs 3 -o p2_e2.md
```

Với E3/F3, đặt thêm `DENSE_MODEL=BAAI/bge-base-en-v1.5` và `DENSE_VECTOR_SIZE=768`.
