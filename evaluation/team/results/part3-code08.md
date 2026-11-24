# Kết quả: part3-code08

- **timestamp**: 2026-11-24T12:01:21
- **git_commit**: c9a03cf-dirty
- **split**: dev
- **n_queries**: 6
- **n_points**: 13137
- **dense_model**: BAAI/bge-small-en-v1.5
- **sparse_model**: prithivida/Splade_PP_en_v1
- **bm25_model**: Qdrant/bm25
- **collection**: team_docs
- **machine**: Windows AMD64, Python 3.11.9

## Tổng hợp

| Method | mrr | ndcg@10 | recall@10 | p@10 | company@5 | dup@5 | unjudged@10 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| hybrid_plus | - | - | - | - | 1.000 | 0.000 | - | 410.3 | 1128.1 |

## Theo nhóm câu hỏi (NDCG@10)

| Method | company | exact_code | numeric_year | rare_term | semantic |
|---|---|---|---|---|---|
| hybrid_plus | - | - | - | - | - |

Ghi chú: unjudged@10 cao (trên 0,2) nghĩa là cấu hình này tìm ra nhiều chunk chưa ai chấm. Chạy lại pool.py, chấm thêm, rồi chạy lại evaluate.py.
