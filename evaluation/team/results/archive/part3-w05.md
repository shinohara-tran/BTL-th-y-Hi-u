# Kết quả: part3-w05

- **timestamp**: 2026-11-24T12:46:01
- **git_commit**: c9a03cf-dirty
- **split**: all
- **n_queries**: 24
- **n_points**: 13137
- **dense_model**: BAAI/bge-small-en-v1.5
- **sparse_model**: prithivida/Splade_PP_en_v1
- **bm25_model**: Qdrant/bm25
- **collection**: team_docs
- **machine**: Windows AMD64, Python 3.11.9

## Tổng hợp

| Method | mrr | ndcg@10 | recall@10 | p@10 | company@5 | dup@5 | unjudged@10 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| bm25 | - | - | - | - | 0.826 | 0.083 | - | 36.7 | 62.9 |
| dense | - | - | - | - | 0.887 | 0.042 | - | 35.9 | 51.1 |
| bm25_dense | - | - | - | - | 0.861 | 0.033 | - | 48.2 | 73.2 |
| sparse | - | - | - | - | 0.861 | 0.058 | - | 90.6 | 187.5 |
| sparse_dense | - | - | - | - | 0.896 | 0.025 | - | 176.7 | 445.3 |
| rerank | - | - | - | - | 0.887 | 0.075 | - | 313.7 | 505.8 |
| hybrid_qp | - | - | - | - | 0.861 | 0.033 | - | 49.6 | 170.3 |
| hybrid_qp_w | - | - | - | - | 0.930 | 0.033 | - | 169.6 | 190.5 |
| hybrid_plus | - | - | - | - | 0.930 | 0.000 | - | 191.2 | 234.1 |

## Theo nhóm câu hỏi (NDCG@10)

| Method | company | exact_code | hybrid | long | numeric_year | rare_term | semantic |
|---|---|---|---|---|---|---|---|
| bm25 | - | - | - | - | - | - | - |
| dense | - | - | - | - | - | - | - |
| bm25_dense | - | - | - | - | - | - | - |
| sparse | - | - | - | - | - | - | - |
| sparse_dense | - | - | - | - | - | - | - |
| rerank | - | - | - | - | - | - | - |
| hybrid_qp | - | - | - | - | - | - | - |
| hybrid_qp_w | - | - | - | - | - | - | - |
| hybrid_plus | - | - | - | - | - | - | - |

Ghi chú: unjudged@10 cao (trên 0,2) nghĩa là cấu hình này tìm ra nhiều chunk chưa ai chấm. Chạy lại pool.py, chấm thêm, rồi chạy lại evaluate.py.
