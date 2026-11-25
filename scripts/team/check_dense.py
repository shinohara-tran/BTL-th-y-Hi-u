"""Check that the dense vectors in Qdrant are real: none is all-zero, and a sample matches the current model.

Read-only. Run from the repo root:
    python scripts/team/check_dense.py                 # collection from config (or QDRANT_COLLECTION)
    python scripts/team/check_dense.py team_docs       # a named collection
Exit code 1 if any dense vector is zero or does not match the model.
"""
from __future__ import annotations

import collections
import sys

import numpy as np
from qdrant_client import QdrantClient

from hybrid_search.config import load_config
from hybrid_search.embeddings.dense import DenseEmbeddingGenerator


def main() -> int:
    cfg = load_config()
    col = sys.argv[1] if len(sys.argv) > 1 else cfg.qdrant.collection_name
    db = QdrantClient(url=cfg.qdrant.url, api_key=cfg.qdrant.api_key, timeout=120)

    zero, total, by_ticker, sample = 0, 0, collections.Counter(), []
    offset = None
    while True:
        pts, offset = db.scroll(col, limit=512, offset=offset, with_payload=["ticker", "text"], with_vectors=["dense"])
        for p in pts:
            total += 1
            if np.linalg.norm(p.vector["dense"]) < 1e-6:
                zero += 1
                by_ticker[p.payload.get("ticker")] += 1
            elif total % 2500 == 1:
                sample.append(p)
        if offset is None:
            break
    print(f"{col}: {total} points, {zero} with an all-zero dense vector {dict(by_ticker) if zero else ''}")

    gen = DenseEmbeddingGenerator(cfg.embeddings.dense_model)
    fresh = gen.embed_texts([p.payload["text"] for p in sample])
    cos = [float(np.dot(p.vector["dense"], f) / (np.linalg.norm(p.vector["dense"]) * np.linalg.norm(f))) for p, f in zip(sample, fresh)]
    print("cosine(stored, re-embedded) on a sample:", [round(c, 3) for c in cos])

    ok = zero == 0 and all(c > 0.99 for c in cos)
    print("OK" if ok else "FAILED: re-embed the dense vectors before measuring anything that uses dense")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
