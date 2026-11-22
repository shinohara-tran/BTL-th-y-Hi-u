"""Tests for the team evaluation kit: metrics, pooling and evaluation with a stub engine."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from hybrid_search.evaluation import team_metrics as tm

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "team"))
import common  # noqa: E402
import evaluate  # noqa: E402
import pool  # noqa: E402


# ---------- metrics ----------

def test_mrr_and_ndcg():
    q = {"a": 2, "b": 1, "c": 0}
    assert tm.mrr(["x", "b", "a"], q) == pytest.approx(0.5)
    assert tm.mrr(["x", "c"], q) == 0.0
    assert tm.ndcg(["a", "b"], q) == pytest.approx(1.0)
    assert 0 < tm.ndcg(["b", "a"], q) < 1.0
    assert tm.ndcg(["x"], {}) == 0.0


def test_recall_uses_all_labeled_relevant_not_just_retrieved():
    q = {"a": 2, "b": 1, "z": 2}  # z is relevant but never retrieved
    assert tm.recall(["a", "b", "x"], q) == pytest.approx(2 / 3)
    assert tm.recall(["a"], {"a": 0}) is None


def test_precision_unjudged_company():
    q = {"a": 2, "b": 0}
    assert tm.precision(["a", "b", "x", "y"], q, k=4) == pytest.approx(0.25)
    assert tm.unjudged_rate(["a", "b", "x", "y"], q, k=4) == pytest.approx(0.5)
    assert tm.company_accuracy(["MSFT", "AAPL", "msft"], ["MSFT"], k=3) == pytest.approx(2 / 3)
    assert tm.company_accuracy(["MSFT"], []) is None


def test_duplicate_rate_ignores_context_header():
    body = "This AI may be developed by Microsoft or others, including our strategic partner, OpenAI. " * 3
    a = "[Microsoft | 10-K FY2024 | Item 1A] " + body
    b = "[Microsoft | 10-K FY2025 | Item 1A] " + body
    c = "Net interest income increased due to higher rates on deposits and loans in the consumer bank."
    assert tm.near_duplicate(a, b)
    assert not tm.near_duplicate(a, c)
    assert tm.duplicate_rate([a, b, c, b]) == pytest.approx(0.5)


def test_cohen_kappa():
    assert tm.cohen_kappa([0, 1, 2, 2], [0, 1, 2, 2]) == pytest.approx(1.0)
    assert tm.cohen_kappa([0, 0, 1, 1], [1, 1, 0, 0]) < 0
    with pytest.raises(ValueError):
        tm.cohen_kappa([0], [0, 1])


def test_percentile():
    assert tm.percentile([1, 2, 3, 4], 50) == pytest.approx(2.5)
    assert tm.percentile([5], 95) == 5


# ---------- stub engine ----------

def hit(cid, ticker="LLY", text="some text"):
    return SimpleNamespace(chunk_id=cid, ticker=ticker, document_type="10-K",
                           fiscal_period="FY2025", section="Item 1A", text=text)


class StubEngine:
    METHOD_NAMES = ["bm25", "dense"]

    def __init__(self, table):
        self.table = table

    def search(self, query, method, k):
        return self.table[method][:k]


QUERIES = [{"id": "q1", "query": "tirzepatide", "category": "rare_term", "expected_tickers": ["LLY"], "split": "test"}]


def test_pool_merges_methods_and_keeps_existing_labels():
    eng = StubEngine({"bm25": [hit("a"), hit("b")], "dense": [hit("b"), hit("c")]})
    existing = [{"qid": "q1", "chunk_id": "b", "best_rank": 5, "found_by": "old", "label": "2", "label_A": "2"}]
    rows = pool.pool(eng, QUERIES, depth=2, methods=["bm25", "dense"], existing=existing)
    by_id = {r["chunk_id"]: r for r in rows}
    assert set(by_id) == {"a", "b", "c"}
    assert by_id["b"]["label"] == "2"  # existing label untouched
    assert by_id["b"]["found_by"] == "bm25|dense|old"
    assert int(by_id["b"]["best_rank"]) == 1


def test_label_file_roundtrip(tmp_path):
    path = tmp_path / "labels.csv"
    common.write_label_rows([{"qid": "q1", "chunk_id": "a", "label": "2", "text": "Lợi nhuận"},
                             {"qid": "q1", "chunk_id": "b", "label": ""}], path)
    assert common.load_qrels(path) == {"q1": {"a": 2}}
    common.write_label_rows([{"qid": "q1", "chunk_id": "a", "label": "3"}], path)
    with pytest.raises(ValueError):
        common.load_qrels(path)


def test_evaluate_with_stub_engine():
    eng = StubEngine({"bm25": [hit("a"), hit("x", ticker="JPM")], "dense": [hit("x", ticker="JPM"), hit("a")]})
    res = evaluate.evaluate(eng, QUERIES, {"q1": {"a": 2}}, ["bm25", "dense"])
    assert res["bm25"]["summary"]["mrr"] == pytest.approx(1.0)
    assert res["dense"]["summary"]["mrr"] == pytest.approx(0.5)
    assert res["bm25"]["summary"]["company@5"] == pytest.approx(0.5)
    md = evaluate.to_markdown({"meta": {"tag": "t"}, "methods": res})
    assert "| bm25 |" in md


def test_queries_file_is_valid():
    qs = common.load_queries()
    assert len(qs) >= 20
    assert {q["split"] for q in qs} <= {"dev", "test"}
