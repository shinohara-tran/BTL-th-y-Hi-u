#!/usr/bin/env bash
# Part 2 on the 13-company team_docs (Dense fixed). Run from repo root, Qdrant (Docker) up.
set -e
export PYTHONIOENCODING=utf-8  # evaluate.py prints Vietnamese; Windows console is cp1252
OUT=docs/team/part2/team13
B="python -m hybrid_search.cli benchmark --k 10 --runs 3"
echo "E0 $(date)"; PYTHONPATH=../BTL-main/src QDRANT_COLLECTION=team_docs $B -o $OUT/E0_goc.md > $OUT/e0.log 2>&1
echo "E1 $(date)"; QDRANT_COLLECTION=team_docs $B -o $OUT/E1_bm25_query_embed.md > $OUT/e1.log 2>&1
echo "E2 build $(date)"; python scripts/team/clone_collection.py team_docs team_docs_e2 > $OUT/e2_build.log 2>&1
echo "E2 $(date)"; QDRANT_COLLECTION=team_docs_e2 $B -o $OUT/E2_splade_bo_idf.md > $OUT/e2.log 2>&1
echo "evaluate part2 $(date)"; QDRANT_COLLECTION=team_docs_e2 python scripts/team/evaluate.py --tag part2 --force > $OUT/evaluate_part2.log 2>&1
echo "E3 build $(date)"; DENSE_MODEL=BAAI/bge-base-en-v1.5 DENSE_VECTOR_SIZE=768 python scripts/team/clone_collection.py team_docs_e2 team_docs_e3 --reembed-dense > $OUT/e3_build.log 2>&1
echo "E3 $(date)"; DENSE_MODEL=BAAI/bge-base-en-v1.5 DENSE_VECTOR_SIZE=768 QDRANT_COLLECTION=team_docs_e3 $B -o $OUT/E3_dense_bge_base.md > $OUT/e3.log 2>&1
echo "DONE $(date)"
