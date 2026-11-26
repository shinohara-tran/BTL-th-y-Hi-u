| Tag | Method | mrr | ndcg@10 | recall@10 | p@10 | company@5 | dup@5 | unjudged@10 | p50 ms | commit | dense |
|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | bm25 | - | - | - | - | 0.826 | 0.083 | - | 2094.1 | unknown | BAAI/bge-small-en-v1.5 |
| baseline | dense | - | - | - | - | 0.783 | 0.083 | - | 2102.1 | unknown | BAAI/bge-small-en-v1.5 |
| baseline | bm25_dense | - | - | - | - | 0.817 | 0.067 | - | 2133.8 | unknown | BAAI/bge-small-en-v1.5 |
| baseline | sparse | - | - | - | - | 0.861 | 0.058 | - | 2156.9 | unknown | BAAI/bge-small-en-v1.5 |
| baseline | sparse_dense | - | - | - | - | 0.852 | 0.050 | - | 2255.7 | unknown | BAAI/bge-small-en-v1.5 |
| baseline | rerank | - | - | - | - | 0.843 | 0.067 | - | 32524.6 | unknown | BAAI/bge-small-en-v1.5 |
| part1 | bm25 | - | - | - | - | 0.817 | 0.075 | - | 39.8 | 7cbbe5c | BAAI/bge-small-en-v1.5 |
| part1 | dense | - | - | - | - | 0.800 | 0.050 | - | 67.3 | 7cbbe5c | BAAI/bge-small-en-v1.5 |
| part1 | bm25_dense | - | - | - | - | 0.835 | 0.033 | - | 70.8 | 7cbbe5c | BAAI/bge-small-en-v1.5 |
| part1 | sparse | - | - | - | - | 0.861 | 0.033 | - | 118.2 | 7cbbe5c | BAAI/bge-small-en-v1.5 |
| part1 | sparse_dense | - | - | - | - | 0.861 | 0.017 | - | 371.3 | 7cbbe5c | BAAI/bge-small-en-v1.5 |
| part1 | rerank | - | - | - | - | 0.878 | 0.025 | - | 43951.0 | 7cbbe5c | BAAI/bge-small-en-v1.5 |
