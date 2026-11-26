"""Phần 3: hybrid search that reads the question, weights the two branches by question type, and drops repeats.

Three methods so each step can be measured on its own (ablation):

    hybrid_qp     query understanding + upstream server-side RRF (equal weights)
    hybrid_qp_w   + weighted RRF computed here (BM25 heavier for codes, Dense heavier for long questions)
    hybrid_plus   + removal of near-duplicate chunks (same boilerplate repeated across years and filings)
"""

from __future__ import annotations

import difflib
import logging
from typing import Dict, List, Optional, Sequence

import numpy as np
from qdrant_client import models

from hybrid_search.config import RetrievalConfig
from hybrid_search.models.filter import MetadataFilter
from hybrid_search.models.search import SearchResult
from hybrid_search.retrieval.base import BaseRetriever
from hybrid_search.retrieval.query_parser import QueryParser

log = logging.getLogger(__name__)

MODES = ("hybrid_qp", "hybrid_qp_w", "hybrid_plus")
ANSWER_SIMILARITY = 0.85  # "OpenAI" vs "OpenAI Global, LLC ("OpenAI")" in the same sentence scores 0.89


def weighted_rrf(ranked_lists: Sequence[List[SearchResult]], weights: Sequence[float], k: int = 60) -> List[SearchResult]:
    """score(chunk) = sum over lists of weight / (k + rank). Keeps the first SearchResult object seen per chunk."""
    scores: Dict[str, float] = {}
    first: Dict[str, SearchResult] = {}
    for results, w in zip(ranked_lists, weights):
        for rank, r in enumerate(results, start=1):
            scores[r.chunk_id] = scores.get(r.chunk_id, 0.0) + w / (k + rank)
            first.setdefault(r.chunk_id, r)
    ordered = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    out = []
    for rank, cid in enumerate(ordered, start=1):
        r = first[cid]
        r.score = round(scores[cid], 6)
        r.rank = rank
        out.append(r)
    return out


def _answer_key(r: SearchResult) -> str:
    """Normalized pinpointed answer; short answers are too generic to call two chunks repeats."""
    key = " ".join(r.exact_answer.lower().split())
    return key if len(key) >= 40 else ""


def drop_near_duplicates(results: List[SearchResult], vectors: Dict[str, Sequence[float]], threshold: float) -> List[SearchResult]:
    """Greedy: keep a chunk unless its dense vector is >= threshold cosine-similar to one already kept,
    or its pinpointed answer sentence matches one already kept (a sentence repeated in a 10-K and a 10-Q
    sits in chunks whose other text differs, so the whole-chunk vectors stay below threshold). Sentences
    count as the same at >= 0.85 character similarity, so small rewordings across filings still match."""
    kept: List[SearchResult] = []
    kept_vecs: List[np.ndarray] = []
    seen_answers: List[str] = []
    for r in results:
        key = _answer_key(r)
        if key and any(difflib.SequenceMatcher(None, key, s).ratio() >= ANSWER_SIMILARITY for s in seen_answers):
            continue
        v = vectors.get(r.chunk_id)
        if v is not None:  # no vector -> cannot judge by vector, keep it
            v = np.asarray(v, dtype=np.float32)
            v = v / (np.linalg.norm(v) or 1.0)
            if any(float(v @ kv) >= threshold for kv in kept_vecs):
                continue
            kept_vecs.append(v)
        kept.append(r)
        if key:
            seen_answers.append(key)
    return kept


class SmartHybridRetriever(BaseRetriever):
    def __init__(self, client, collection_name: str, parser: QueryParser,
                 bm25: BaseRetriever, dense: BaseRetriever, server_hybrid: BaseRetriever,
                 settings: RetrievalConfig, mode: str):
        super().__init__(client=client, collection_name=collection_name)
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.parser, self.bm25, self.dense, self.server_hybrid = parser, bm25, dense, server_hybrid
        self.settings, self.mode = settings, mode

    @property
    def name(self) -> str:
        return self.mode

    def lexical_weight(self, query_type: str) -> float:
        return {"code": self.settings.lexical_weight_code,
                "concept": self.settings.lexical_weight_concept}.get(query_type, 0.5)

    def search(self, query: str, k: int = 10, filters: Optional[MetadataFilter] = None,
               prefetch_k: int = 50) -> List[SearchResult]:
        parsed = self.parser.parse(query)
        merged = parsed.merge_into(filters)

        if self.mode == "hybrid_qp":
            results = self.server_hybrid.search(parsed.text, k=k, filters=merged, prefetch_k=prefetch_k)
        else:
            w = self.lexical_weight(parsed.query_type)
            lexical = self.bm25.search(parsed.text, k=prefetch_k, filters=merged)
            semantic = self.dense.search(parsed.text, k=prefetch_k, filters=merged)
            results = weighted_rrf([lexical, semantic], [w, 1.0 - w], k=self.settings.rrf_constant)
            if self.mode == "hybrid_plus":
                pool = results[: max(k * 3, 20)]
                results = drop_near_duplicates(pool, self._dense_vectors([r.chunk_id for r in pool]),
                                               self.settings.dedup_threshold)
            results = results[:k]
            for rank, r in enumerate(results, start=1):
                r.rank = rank

        for r in results:
            r.retrieval_method = self.mode
        return results

    def _dense_vectors(self, chunk_ids: List[str]) -> Dict[str, Sequence[float]]:
        if not chunk_ids:
            return {}
        try:
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(must=[models.FieldCondition(key="chunk_id", match=models.MatchAny(any=chunk_ids))]),
                limit=len(chunk_ids),
                with_payload=["chunk_id"],
                with_vectors=["dense"],
            )
        except Exception as exc:  # dedup is an improvement, not a requirement: search still answers without it
            log.warning("Could not fetch dense vectors for dedup, skipping it: %s", exc)
            return {}
        out = {}
        for p in points:
            vec = p.vector.get("dense") if isinstance(p.vector, dict) else p.vector
            if vec is not None:
                out[str((p.payload or {}).get("chunk_id", p.id))] = vec
        return out
