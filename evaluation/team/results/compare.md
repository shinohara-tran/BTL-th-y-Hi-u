Baseline used in this Part 1 comparison: [baseline_part1.json](baseline_part1.json).

| Tag | Method | mrr | ndcg@10 | recall@10 | p@10 | company@5 | dup@5 | unjudged@10 | p50 ms | commit | dense |
|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline_part1 | bm25 | - | - | - | - | 0.826 | 0.083 | - | 2069.2 | unknown | BAAI/bge-small-en-v1.5 |
| baseline_part1 | dense | - | - | - | - | 0.000 | 0.000 | - | 2092.6 | unknown | BAAI/bge-small-en-v1.5 |
| baseline_part1 | bm25_dense | - | - | - | - | 0.391 | 0.017 | - | 2092.2 | unknown | BAAI/bge-small-en-v1.5 |
| baseline_part1 | sparse | - | - | - | - | 0.861 | 0.058 | - | 2116.7 | unknown | BAAI/bge-small-en-v1.5 |
| baseline_part1 | sparse_dense | - | - | - | - | 0.478 | 0.017 | - | 2187.3 | unknown | BAAI/bge-small-en-v1.5 |
| baseline_part1 | rerank | - | - | - | - | 0.870 | 0.092 | - | 2319.5 | unknown | BAAI/bge-small-en-v1.5 |
| part1 | bm25 | - | - | - | - | 0.826 | 0.083 | - | 2072.8 | unknown | BAAI/bge-small-en-v1.5 |
| part1 | dense | - | - | - | - | 0.278 | 0.000 | - | 2076.2 | unknown | BAAI/bge-small-en-v1.5 |
| part1 | bm25_dense | - | - | - | - | 0.530 | 0.025 | - | 2089.0 | unknown | BAAI/bge-small-en-v1.5 |
| part1 | sparse | - | - | - | - | 0.861 | 0.058 | - | 2114.1 | unknown | BAAI/bge-small-en-v1.5 |
| part1 | sparse_dense | - | - | - | - | 0.565 | 0.025 | - | 2227.6 | unknown | BAAI/bge-small-en-v1.5 |
| part1 | rerank | - | - | - | - | 0.870 | 0.083 | - | 2355.2 | unknown | BAAI/bge-small-en-v1.5 |
