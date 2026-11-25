"""Stage-2 ranking of financial filing excerpts with a FastEmbed cross-encoder."""

from __future__ import annotations

import math
import os
import re
from threading import Lock
from typing import Optional

from fastembed.rerank.cross_encoder import TextCrossEncoder
from hybrid_search.models.search import SearchResult
from hybrid_search.retrieval.extractor import AnswerExtractor, requested_period


def period_conflict(period, result):
    if period is None:
        return False
    year, kind = period
    # The contextual prefix describes the filing, not the columns in this table.
    body = re.sub(r"^\s*\[[^\]]*\]\s*", "", result.text).lower()
    months = re.search(r"\b(?:three|six|nine|3|6|9)[ -]+months?\b", body)
    annual_columns = re.search(r"\b(years? ended|full fiscal year|twelve months|12 months)\b", body)
    if kind == "annual":
        if annual_columns:
            return False
        return bool(months or result.document_type == "10-Q")
    quarter_label = re.search(r"\bq([1-4])\s+(?:fy\s*)?(20\d{2})\s+form\s+10-q", body)
    if quarter_label:
        return (quarter_label[1], quarter_label[2]) != (kind, year)
    return result.document_type in {"10-K", "20-F"} and not (months or "quarter" in body)


class NeuralReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self.batch_size = int(os.environ.get("HYBRID_RERANK_BATCH_SIZE", "2"))
        if self.batch_size < 1:
            raise ValueError("HYBRID_RERANK_BATCH_SIZE must be positive")
        self._model = None
        self._load_lock = Lock()

    def rerank(
        self, query: str, results: list[SearchResult], top_k: Optional[int] = None
    ) -> list[SearchResult]:
        if not results:
            return []

        with self._load_lock:
            if self._model is None:
                self._model = TextCrossEncoder(model_name=self.model_name)
        scores = self._model.rerank(
            query, [result.text for result in results], batch_size=self.batch_size
        )
        ranked = sorted(zip(scores, results, strict=True), key=lambda pair: pair[0], reverse=True)
        period = requested_period(query)
        # Prefer a verified table column before cutting the displayed results.
        evidence = {}
        if AnswerExtractor.table_search_terms(query):
            evidence = {
                result.chunk_id: AnswerExtractor.extract(query, result.text)
                for _, result in ranked
            }
        ranked.sort(key=lambda pair: (
            not (evidence and evidence[pair[1].chunk_id].exact_answer),
            period_conflict(period, pair[1]),
        ))

        selected = []
        for rank, (score, result) in enumerate(ranked[:top_k or len(results)], start=1):
            extracted = evidence.get(result.chunk_id) or AnswerExtractor.extract(
                query, result.text, company=result.company, ticker=result.ticker
            )
            result.rank = rank
            result.score = round(float(score), 4)
            result.retrieval_method = "rerank"
            result.exact_answer = extracted.exact_answer
            result.highlighted_text = extracted.highlighted_text
            probability = 1 / (1 + math.exp(-max(-60, min(60, float(score)))))
            result.answer_confidence = round(extracted.confidence * probability, 4)
            selected.append(result)
        return selected
