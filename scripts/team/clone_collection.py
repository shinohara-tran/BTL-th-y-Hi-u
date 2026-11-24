"""Copy every point (payload + all vectors) from one collection into a new one.

The new collection is created by QdrantIndexManager with the current code config,
so a config-only change (e.g. the sparse IDF modifier) can be tested without
re-embedding 8,670 chunks. With --reembed-dense, only the dense vector is
recomputed (model from DENSE_MODEL / config); bm25 and sparse vectors are reused.

Usage (Qdrant server running, or run from the folder that holds embedded qdrant_data):
    python scripts/team/clone_collection.py team_docs team_docs_e2
    DENSE_MODEL=BAAI/bge-base-en-v1.5 DENSE_VECTOR_SIZE=768 \
        python scripts/team/clone_collection.py team_docs_e2 team_docs_e3 --reembed-dense
"""

from __future__ import annotations

import os
import sys
import time

from qdrant_client import models

from hybrid_search.config import load_config
from hybrid_search.embeddings.dense import DenseEmbeddingGenerator
from hybrid_search.indexing.qdrant_index import QdrantIndexManager


def main(src: str, dst: str, reembed_dense: bool = False) -> None:
    os.environ["QDRANT_COLLECTION"] = dst
    config = load_config()
    manager = QdrantIndexManager(config)
    client = manager.client
    if not client.collection_exists(src):
        sys.exit(f"Source collection '{src}' not found")
    if src == dst:
        sys.exit("Source and destination must differ")
    dense_gen = DenseEmbeddingGenerator(config.embeddings.dense_model) if reembed_dense else None
    manager.create_collection(recreate=True)

    total_src = client.count(src).count
    offset, copied, started = None, 0, time.time()
    while True:
        points, offset = client.scroll(src, limit=128, offset=offset, with_payload=True, with_vectors=True)
        if points:
            if dense_gen:
                new_dense = dense_gen.embed_texts([p.payload["text"] for p in points])
                for p, vec in zip(points, new_dense):
                    p.vector["dense"] = vec
            client.upsert(dst, points=[
                models.PointStruct(id=p.id, vector=p.vector, payload=p.payload) for p in points
            ])
            copied += len(points)
            elapsed = time.time() - started
            print(f"{copied}/{total_src} points | {elapsed / 60:.1f} min", flush=True)
        if offset is None:
            break

    total = client.count(dst).count
    assert total == total_src == copied, (total, total_src, copied)
    print(f"Copied {copied} points: {src} -> {dst} in {(time.time() - started) / 60:.1f} min")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], reembed_dense="--reembed-dense" in sys.argv[3:])
