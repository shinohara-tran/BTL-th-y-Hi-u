# Kết quả: baseline

- **timestamp**: 2026-11-24T10:02:25
- **git_commit**: a746b05-dirty
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
| bm25 | - | - | - | - | 0.826 | 0.083 | - | 37.2 | 53.7 |
| dense | - | - | - | - | 0.887 | 0.042 | - | 57.1 | 118.1 |
| bm25_dense | - | - | - | - | 0.852 | 0.033 | - | 146.2 | 274.3 |
| sparse | - | - | - | - | 0.861 | 0.058 | - | 162.8 | 657.7 |
| sparse_dense | - | - | - | - | 0.904 | 0.025 | - | 304.3 | 494.6 |
| rerank | - | - | - | - | 0.887 | 0.075 | - | 366.6 | 494.8 |

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
