"""Team evaluation metrics on human relevance labels (qrels).

The upstream benchmark marks a chunk as relevant when it contains a few keywords,
which favours BM25 and makes Recall@10 equal Hit Rate@10. These functions score
results against graded labels written by people instead:

    0 = not relevant, 1 = partly relevant, 2 = answers the question

A qrels mapping is {chunk_id: grade} for one query. Chunks without a label are
"unjudged" and count as not relevant; report unjudged_rate next to the scores so
a new configuration that finds many unlabeled chunks is noticed and re-pooled.
"""

from __future__ import annotations

import math
import re
from typing import Dict, List, Optional, Sequence

Qrels = Dict[str, int]


def mrr(ranked_ids: Sequence[str], qrels: Qrels, k: int = 10, min_grade: int = 1) -> float:
    """Reciprocal rank of the first chunk with grade >= min_grade within the top k."""
    for rank, cid in enumerate(ranked_ids[:k], start=1):
        if qrels.get(cid, 0) >= min_grade:
            return 1.0 / rank
    return 0.0


def ndcg(ranked_ids: Sequence[str], qrels: Qrels, k: int = 10) -> float:
    """Graded NDCG@k with gain 2^grade - 1. The ideal ranking uses every labeled chunk."""
    def dcg(grades: Sequence[int]) -> float:
        return sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(grades))

    actual = dcg([qrels.get(cid, 0) for cid in ranked_ids[:k]])
    ideal = dcg(sorted(qrels.values(), reverse=True)[:k])
    return actual / ideal if ideal > 0 else 0.0


def recall(ranked_ids: Sequence[str], qrels: Qrels, k: int = 10, min_grade: int = 1) -> Optional[float]:
    """Share of all labeled-relevant chunks that appear in the top k. None if the query has none."""
    relevant = {cid for cid, g in qrels.items() if g >= min_grade}
    if not relevant:
        return None
    return len(relevant.intersection(ranked_ids[:k])) / len(relevant)


def precision(ranked_ids: Sequence[str], qrels: Qrels, k: int = 10, min_grade: int = 1) -> float:
    top = ranked_ids[:k]
    if not top:
        return 0.0
    return sum(1 for cid in top if qrels.get(cid, 0) >= min_grade) / len(top)


def unjudged_rate(ranked_ids: Sequence[str], qrels: Qrels, k: int = 10) -> float:
    """Share of the top k that nobody has labeled yet. High values mean: re-pool and label."""
    top = ranked_ids[:k]
    if not top:
        return 0.0
    return sum(1 for cid in top if cid not in qrels) / len(top)


def company_accuracy(ranked_tickers: Sequence[str], expected: Sequence[str], k: int = 5) -> Optional[float]:
    """Share of the top k that belong to one of the expected companies. None if no company is expected."""
    if not expected:
        return None
    top = ranked_tickers[:k]
    if not top:
        return 0.0
    wanted = {t.upper() for t in expected}
    return sum(1 for t in top if (t or "").upper() in wanted) / len(top)


_WORD = re.compile(r"[a-z0-9]+")


def _words(text: str) -> List[str]:
    return _WORD.findall(text.lower())


def _shingles(words: List[str], n: int) -> set:
    if len(words) < n:
        return {" ".join(words)}
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def strip_context_header(text: str) -> str:
    """Drop the leading '[Company | Form | Period ...]' header so two years of the same text compare equal."""
    return re.sub(r"^\s*\[[^\]]*\]\s*", "", text or "")


def near_duplicate(a: str, b: str, threshold: float = 0.6, n: int = 5) -> bool:
    """True when two chunks share most of their word 5-grams (Jaccard >= threshold)."""
    wa, wb = _words(strip_context_header(a)), _words(strip_context_header(b))
    if not wa or not wb:
        return False
    sa, sb = _shingles(wa, n), _shingles(wb, n)
    return len(sa & sb) / len(sa | sb) >= threshold


def duplicate_rate(texts: Sequence[str], k: int = 5, threshold: float = 0.6) -> float:
    """Share of the top k results that near-duplicate a result ranked above them."""
    top = list(texts[:k])
    if not top:
        return 0.0
    dups = 0
    for i in range(1, len(top)):
        if any(near_duplicate(top[i], top[j], threshold) for j in range(i)):
            dups += 1
    return dups / len(top)


def cohen_kappa(labels_a: Sequence[int], labels_b: Sequence[int]) -> float:
    """Cohen's kappa for two annotators labeling the same items."""
    if len(labels_a) != len(labels_b):
        raise ValueError("Both annotators must label the same items")
    n = len(labels_a)
    if n == 0:
        return float("nan")
    cats = sorted(set(labels_a) | set(labels_b))
    observed = sum(1 for x, y in zip(labels_a, labels_b) if x == y) / n
    expected = sum((list(labels_a).count(c) / n) * (list(labels_b).count(c) / n) for c in cats)
    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1 - expected)


def percentile(values: Sequence[float], p: float) -> float:
    """Linear-interpolated percentile, p in [0, 100]."""
    if not values:
        return float("nan")
    xs = sorted(values)
    pos = (len(xs) - 1) * p / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def mean(values: Sequence[Optional[float]]) -> Optional[float]:
    xs = [v for v in values if v is not None]
    return sum(xs) / len(xs) if xs else None
