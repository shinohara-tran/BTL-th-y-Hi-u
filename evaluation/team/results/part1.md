# Kết quả: part1

- **timestamp**: 2026-11-25T21:54:04
- **git_commit**: 7cbbe5c
- **split**: all
- **n_queries**: 24
- **n_points**: 14022
- **dense_model**: BAAI/bge-small-en-v1.5
- **sparse_model**: prithivida/Splade_PP_en_v1
- **bm25_model**: Qdrant/bm25
- **collection**: team_docs_final
- **machine**: Windows AMD64, Python 3.11.9

## Tổng hợp

| Method | mrr | ndcg@10 | recall@10 | p@10 | company@5 | dup@5 | unjudged@10 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| bm25 | - | - | - | - | 0.817 | 0.075 | - | 39.8 | 96.5 |
| dense | - | - | - | - | 0.800 | 0.050 | - | 67.3 | 134.1 |
| bm25_dense | - | - | - | - | 0.835 | 0.033 | - | 70.8 | 155.6 |
| sparse | - | - | - | - | 0.861 | 0.033 | - | 118.2 | 286.2 |
| sparse_dense | - | - | - | - | 0.861 | 0.017 | - | 371.3 | 505.3 |
| rerank | - | - | - | - | 0.878 | 0.025 | - | 43951.0 | 62201.0 |

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
