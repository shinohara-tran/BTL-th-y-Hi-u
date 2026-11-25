# Kết quả: part3

- **timestamp**: 2026-11-24T11:49:54
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
| bm25 | - | - | - | - | 0.826 | 0.083 | - | 35.5 | 56.7 |
| dense | - | - | - | - | 0.887 | 0.042 | - | 77.0 | 151.1 |
| bm25_dense | - | - | - | - | 0.852 | 0.033 | - | 69.2 | 106.9 |
| sparse | - | - | - | - | 0.861 | 0.058 | - | 150.3 | 220.8 |
| sparse_dense | - | - | - | - | 0.904 | 0.025 | - | 249.6 | 442.7 |
| rerank | - | - | - | - | 0.887 | 0.075 | - | 450.0 | 595.2 |
| hybrid_qp | - | - | - | - | 0.878 | 0.033 | - | 72.7 | 145.7 |
| hybrid_qp_w | - | - | - | - | 0.930 | 0.033 | - | 221.3 | 266.0 |
| hybrid_plus | - | - | - | - | 0.922 | 0.000 | - | 293.5 | 711.3 |

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
