| Tag | Method | mrr | ndcg@10 | recall@10 | p@10 | company@5 | dup@5 | unjudged@10 | p50 ms | commit | dense |
|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | bm25 | - | - | - | - | 0.826 | 0.083 | - | 2094.1 | unknown | BAAI/bge-small-en-v1.5 |
| baseline | dense | - | - | - | - | 0.783 | 0.083 | - | 2102.1 | unknown | BAAI/bge-small-en-v1.5 |
| baseline | bm25_dense | - | - | - | - | 0.817 | 0.067 | - | 2133.8 | unknown | BAAI/bge-small-en-v1.5 |
| baseline | sparse | - | - | - | - | 0.861 | 0.058 | - | 2156.9 | unknown | BAAI/bge-small-en-v1.5 |
| baseline | sparse_dense | - | - | - | - | 0.852 | 0.050 | - | 2255.7 | unknown | BAAI/bge-small-en-v1.5 |
| baseline | rerank | - | - | - | - | 0.843 | 0.067 | - | 32524.6 | unknown | BAAI/bge-small-en-v1.5 |
| part1 | bm25 | - | - | - | - | 0.826 | 0.083 | - | 2086.0 | unknown | BAAI/bge-small-en-v1.5 |
| part1 | dense | - | - | - | - | 0.783 | 0.083 | - | 2089.2 | unknown | BAAI/bge-small-en-v1.5 |
| part1 | bm25_dense | - | - | - | - | 0.826 | 0.067 | - | 2099.2 | unknown | BAAI/bge-small-en-v1.5 |
| part1 | sparse | - | - | - | - | 0.861 | 0.058 | - | 2146.0 | unknown | BAAI/bge-small-en-v1.5 |
| part1 | sparse_dense | - | - | - | - | 0.861 | 0.050 | - | 2208.2 | unknown | BAAI/bge-small-en-v1.5 |
| part1 | rerank | - | - | - | - | 0.843 | 0.067 | - | 43054.5 | unknown | BAAI/bge-small-en-v1.5 |
