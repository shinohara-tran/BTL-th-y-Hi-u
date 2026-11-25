# Kết quả: baseline

- **timestamp**: 2026-11-25T01:01:38
- **git_commit**: unknown
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
| bm25 | - | - | - | - | 0.826 | 0.083 | - | 2069.2 | 2103.1 |
| dense | - | - | - | - | 0.000 | 0.000 | - | 2092.6 | 2153.8 |
| bm25_dense | - | - | - | - | 0.391 | 0.017 | - | 2092.2 | 2115.9 |
| sparse | - | - | - | - | 0.861 | 0.058 | - | 2116.7 | 2158.3 |
| sparse_dense | - | - | - | - | 0.478 | 0.017 | - | 2187.3 | 2274.7 |
| rerank | - | - | - | - | 0.870 | 0.092 | - | 2319.5 | 2445.0 |

## Theo nhóm câu hỏi (NDCG@10)

| Method | company | exact_code | hybrid | long | numeric_year | rare_term | semantic |
|---|---|---|---|---|---|---|---|
| bm25 | - | - | - | - | - | - | - |
| dense | - | - | - | - | - | - | - |
| bm25_dense | - | - | - | - | - | - | - |
| sparse | - | - | - | - | - | - | - |
| sparse_dense | - | - | - | - | - | - | - |
| rerank | - | - | - | - | - | - | - |

Ghi chú: unjudged@10 cao (trên 0,2) nghĩa là cấu hình này tìm ra nhiều chunk chưa ai chấm. Chạy lại pool.py, chấm thêm, rồi chạy lại evaluate.py.
