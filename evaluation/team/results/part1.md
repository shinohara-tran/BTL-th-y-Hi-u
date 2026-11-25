# Kết quả: part1

- **timestamp**: 2026-11-25T16:44:59
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
| bm25 | - | - | - | - | 0.826 | 0.083 | - | 2086.0 | 2169.3 |
| dense | - | - | - | - | 0.783 | 0.083 | - | 2089.2 | 2160.5 |
| bm25_dense | - | - | - | - | 0.826 | 0.067 | - | 2099.2 | 2141.8 |
| sparse | - | - | - | - | 0.861 | 0.058 | - | 2146.0 | 2820.4 |
| sparse_dense | - | - | - | - | 0.861 | 0.050 | - | 2208.2 | 2346.5 |
| rerank | - | - | - | - | 0.843 | 0.067 | - | 43054.5 | 52356.1 |

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
