# Minh chứng Phần 2: Ba cách tạo vector (BM25, Dense, SPLADE)

Nhóm 3, Topic 3 Hybrid Search. Chạy ngày 20 và 22/11/2026, trên cùng một máy và cùng 8.670 chunk (dữ liệu được đóng băng).

## Các thử nghiệm

| Mã | Thay đổi | Ngăn (collection) | Cách tạo | File báo cáo |
|---|---|---|---|---|
| E0 | Bản gốc của tác giả | `financial_docs` | Index đầy đủ, khoảng 100 phút | `1_bao_cao/E0_goc.md` |
| E1 | BM25: câu hỏi dùng `query_embed()` thay cho `embed()` | `financial_docs` | Không cần index lại | `1_bao_cao/E1_bm25_query_embed.md` |
| E2 | E1 + SPLADE bỏ `Modifier.IDF` | `financial_docs_e2` | Chép vector, 36 giây | `1_bao_cao/E2_splade_bo_idf.md` |
| E3 | E2 + Dense `bge-base-en-v1.5` (768 chiều) | `financial_docs_e3` | Chỉ tạo lại Dense, 45,4 phút | `1_bao_cao/E3_dense_bge_base.md` |

## Kết quả (k = 10, 25 câu hỏi)

MRR:

| | BM25 | Dense | BM25+Dense | SPLADE | SPLADE+Dense | Rerank |
|---|---|---|---|---|---|---|
| E0 | 0,933 | 0,827 | 0,926 | 0,877 | 0,840 | 0,893 |
| E1 | 0,933 | 0,827 | 0,926 | 0,877 | 0,840 | 0,893 |
| E2 | 0,933 | 0,827 | 0,926 | **0,913** | **0,875** | **0,896** |
| E3 | 0,933 | **0,831** | 0,908 | 0,913 | **0,890** | 0,895 |

NDCG@10:

| | BM25 | Dense | BM25+Dense | SPLADE | SPLADE+Dense | Rerank |
|---|---|---|---|---|---|---|
| E0 | 0,918 | 0,830 | 0,904 | 0,907 | 0,866 | 0,889 |
| E1 | 0,919 | 0,830 | 0,904 | 0,907 | 0,866 | 0,889 |
| E2 | 0,919 | 0,830 | 0,904 | 0,901 | 0,871 | 0,896 |
| E3 | 0,919 | 0,837 | 0,894 | 0,901 | 0,885 | 0,896 |

Độ trễ trung vị (p50) của Dense: E2 là 31 ms, E3 là 54 ms.

## Kết luận

1. **E1**: gần như không thay đổi, NDCG của BM25 tăng 0,0008. Hàm cũ nhân mọi từ trong câu hỏi với cùng một hệ số (1,661), nên thứ hạng giữ nguyên. Chỉ câu hỏi có từ lặp lại mới bị lệch.
2. **E2**: thay đổi rõ nhất. MRR của SPLADE tăng từ 0,877 lên 0,913; Recall@10 của SPLADE+Dense và Rerank tăng từ 0,92 lên 0,96. Đổi lại, nhóm câu hỏi khái niệm (Semantic) giảm từ 0,689 xuống 0,625.
3. **E3**: Dense tốt hơn hẳn ở thuật ngữ hiếm (NDCG 0,880 lên 0,953), nhưng tổng thể gần như không đổi. BM25+Dense giảm nhẹ, độ trễ Dense tăng 75%. Với bộ đánh giá này, nâng cấp chưa đáng với chi phí.
4. BM25 dùng một mình vẫn có MRR cao nhất (0,933).

## Giới hạn

- Chỉ có 25 câu hỏi. MRR chênh dưới khoảng 0,04 tương ứng 1 đến 2 câu đổi thứ hạng, chưa đủ để kết luận chắc chắn.
- Benchmark chấm theo từ khóa có sẵn (`evaluation/benchmark.py`), nên thiên vị BM25 và đánh giá thấp Dense.
- 23% chunk dài quá 512 token và bị cắt đuôi khi tạo vector Dense hoặc SPLADE. Đây là lỗi của Phần 1; bge-base cũng chỉ đọc tối đa 512 token.
- Chạy trên Qdrant embedded, nên độ trễ chỉ dùng để so sánh tương đối giữa các thử nghiệm.

## Nội dung thư mục

| Thư mục | Nội dung |
|---|---|
| `1_bao_cao/` | Báo cáo benchmark đầy đủ của từng thử nghiệm. Chỉ bảng 1 đến 3 là số đo; mục 5 đến 7 là chữ viết sẵn trong `report.py` |
| `2_log/` | Toàn bộ output khi chạy. `e3_build.log` ghi tiến độ và thời gian tạo vector Dense |
| `3_code/phan2_sua_doi.diff` | Các dòng code đã sửa so với commit gốc `16682dd` |
| `3_code/clone_collection.py` | Script tạo ngăn mới bằng cách chép vector |
| `4_cau_hinh/qdrant_meta.json` | Cấu hình các ngăn. Ngăn `financial_docs_e2` có `"sparse": modifier null`; ngăn `financial_docs_e3` có dense `size 768` |
| `4_cau_hinh/thong_tin_may.txt` | CPU, RAM, phiên bản Python và thư viện |

## Chạy lại

Chạy từ thư mục `D:\PTTC\p2_lab` (nơi chứa `qdrant_data`):

```
set QDRANT_COLLECTION=financial_docs_e2
python -m hybrid_search.cli benchmark --k 10 --runs 3 -o p2_e2.md
```

Với E3, đặt thêm `DENSE_MODEL=BAAI/bge-base-en-v1.5` và `DENSE_VECTOR_SIZE=768`.
