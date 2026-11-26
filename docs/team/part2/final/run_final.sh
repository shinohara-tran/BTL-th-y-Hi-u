#!/usr/bin/env bash
# Part 2 on team_docs_final (14,022 chunks, Part 1 chunking). Run from repo root with Qdrant (Docker) up.
# F0: original code + SPLADE with IDF (rebuilt by copying vectors with main's index code)
# F1: + BM25 query_embed   F2: + SPLADE without IDF (= team_docs_final as shipped)   F3: + Dense bge-base
set -e
export PYTHONIOENCODING=utf-8  # evaluate.py prints Vietnamese; Windows console is cp1252
OUT=docs/team/part2/final
B="python -m hybrid_search.cli benchmark --k 10 --runs 3"
MAIN=../BTL-main/src
echo "F0 build $(date)"; PYTHONPATH=$MAIN python scripts/team/clone_collection.py team_docs_final team_docs_final_idf > $OUT/f0_build.log 2>&1
echo "F0 $(date)"; PYTHONPATH=$MAIN QDRANT_COLLECTION=team_docs_final_idf $B -o $OUT/F0_goc.md > $OUT/f0.log 2>&1
echo "F1 $(date)"; QDRANT_COLLECTION=team_docs_final_idf $B -o $OUT/F1_bm25_query_embed.md > $OUT/f1.log 2>&1
echo "F2 $(date)"; QDRANT_COLLECTION=team_docs_final $B -o $OUT/F2_splade_bo_idf.md > $OUT/f2.log 2>&1
echo "evaluate $(date)"; QDRANT_COLLECTION=team_docs_final python scripts/team/evaluate.py --tag part2 --force > $OUT/evaluate_part2.log 2>&1
echo "F3 build $(date)"; DENSE_MODEL=BAAI/bge-base-en-v1.5 DENSE_VECTOR_SIZE=768 python scripts/team/clone_collection.py team_docs_final team_docs_final_e3 --reembed-dense > $OUT/f3_build.log 2>&1
echo "F3 $(date)"; DENSE_MODEL=BAAI/bge-base-en-v1.5 DENSE_VECTOR_SIZE=768 QDRANT_COLLECTION=team_docs_final_e3 $B -o $OUT/F3_dense_bge_base.md > $OUT/f3.log 2>&1
echo "DONE $(date)"
