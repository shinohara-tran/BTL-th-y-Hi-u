# Kết quả: part1

- **timestamp**: 2026-11-25T01:07:09
- **git_commit**: unknown
- **split**: all
- **n_queries**: 24
- **n_points**: 13137
- **dense_model**: BAAI/bge-small-en-v1.5
- **sparse_model**: prithivida/Splade_PP_en_v1
- **bm25_model**: Qdrant/bm25
- **collection**: team_docs_p1
- **machine**: Windows AMD64, Python 3.11.9

## Tổng hợp

| Method | mrr | ndcg@10 | recall@10 | p@10 | company@5 | dup@5 | unjudged@10 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| bm25 | - | - | - | - | 0.826 | 0.083 | - | 2072.8 | 2106.9 |
| dense | - | - | - | - | 0.278 | 0.000 | - | 2076.2 | 2205.0 |
| bm25_dense | - | - | - | - | 0.530 | 0.025 | - | 2089.0 | 2115.1 |
| sparse | - | - | - | - | 0.861 | 0.058 | - | 2114.1 | 2257.9 |
| sparse_dense | - | - | - | - | 0.565 | 0.025 | - | 2227.6 | 2319.8 |
| rerank | - | - | - | - | 0.870 | 0.083 | - | 2355.2 | 2571.6 |

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
