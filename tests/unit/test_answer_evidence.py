"""Regression tests for the evidence required by the direct-answer card."""

import unittest

from hybrid_search.retrieval.extractor import AnswerExtractor


TABLE = (
    "[Apple Inc. (AAPL) | 10-K FY2025]\n\n"
    "Net sales by category (dollars in millions): | 2025 | Change | 2024 | "
    "Services (1) | 109,158 | 14 | % | 96,169 | Total net sales | 416,161"
)


class EvidenceTests(unittest.TestCase):
    def test_services_sales_uses_actual_year_column_and_ignores_change(self):
        answer = AnswerExtractor.extract("What was Services revenue in fiscal 2024?", TABLE)
        self.assertEqual(answer.exact_answer, "Services net sales - FY2024: $96,169 million")
        self.assertGreaterEqual(answer.confidence, 0.3)

    def test_services_sales_abstains_without_year_columns(self):
        answer = AnswerExtractor.extract(
            "What were Services net sales in fiscal 2024?",
            TABLE.replace("2025 | Change | 2024 | ", ""),
        )
        self.assertEqual(answer.confidence, 0.0)
        self.assertEqual(answer.exact_answer, "")
        self.assertIn("96,169", answer.highlighted_text)

    def test_basic_eps_rejects_share_count(self):
        answer = AnswerExtractor.extract(
            "What was basic EPS in fiscal 2024?",
            "[10-K FY2024]\n\nWeighted-average basic shares outstanding were 15,343,783.",
        )
        self.assertEqual(answer.confidence, 0.0)
from types import SimpleNamespace

from hybrid_search.models.search import SearchResult
from hybrid_search.retrieval.engine import SearchEngine
from hybrid_search.retrieval.reranker import NeuralReranker


def test_rerank_recovers_verified_table_before_top_k():
    def result(chunk_id, text):
        return SearchResult(
            chunk_id=chunk_id, document_id="doc", score=1, rank=1, text=text,
            company="Apple Inc.", ticker="AAPL", document_type="10-K",
            filing_date="2024-11-01", fiscal_period="FY2024", section="Item 8",
            retrieval_method="bm25",
        )

    incomplete = result("partial", TABLE.replace("2025 | Change | 2024 | ", ""))
    verified = result("complete", TABLE)
    engine = SearchEngine.__new__(SearchEngine)
    engine.retrievers = {
        "sparse_dense": SimpleNamespace(search=lambda **kwargs: [incomplete]),
        "bm25": SimpleNamespace(search=lambda **kwargs: [verified]),
    }
    engine.reranker = NeuralReranker()
    engine.reranker.max_passage_tokens = 0
    engine.reranker._model = SimpleNamespace(rerank=lambda *args, **kwargs: [5.0, 1.0])

    selected, = engine.search("What was Services revenue in fiscal 2024?", method="rerank", k=1)
    assert selected.chunk_id == "complete"
    assert selected.exact_answer == "Services net sales - FY2024: $96,169 million"
    assert selected.answer_confidence >= 0.3


ANNUAL_MARGIN = (
    "[Apple Inc. (AAPL) | 10-K FY2025]\n\n"
    "Gross Margin | 2025 | 2024 | 2023 | Gross margin: | Products | $ | "
    "112,887 | 109,633 | 108,803 | Gross margin percentage: | "
    "Products | 36.8 | % | 37.2 | % | 36.5 | % | Services"
)
QUARTER_MARGIN = (
    "[Apple Inc. (AAPL) | 10-Q Q-2025-08]\n\n"
    "Q3 2025 Form 10-Q | Three Months Ended | Nine Months Ended | "
    "June 28, 2025 | June 29, 2024 | June 28, 2025 | June 29, 2024 | "
    "Gross margin: | Products | 22,993 | Gross margin percentage: | "
    "Products | 34.5 | % | 35.3 | % | 36.9 | % | 37.5 | % | Services"
)


def test_annual_gross_margin_selects_percentage_for_requested_year():
    answer = AnswerExtractor.extract(
        "What was Apple's Products gross margin percentage for full fiscal year 2025?",
        ANNUAL_MARGIN,
    )
    assert answer.exact_answer == "Products gross margin percentage - FY2025: 36.8%"


def test_quarter_gross_margin_selects_three_month_column():
    answer = AnswerExtractor.extract(
        "What was Apple's Products gross margin percentage in Q3 FY2025?",
        QUARTER_MARGIN.replace("June", "Jun."),
    )
    assert answer.exact_answer == "Products gross margin percentage - Q3 FY2025: 34.5%"


def test_quarter_gross_margin_rejects_unknown_quarter_and_missing_columns():
    query = "What was Apple's Products gross margin percentage in Q3 FY2025?"
    for body in (
        QUARTER_MARGIN.replace("Q3 2025 Form 10-Q", "Form 10-Q"),
        QUARTER_MARGIN.replace("Q3 2025 Form 10-Q", "Q2 2025 Form 10-Q"),
        QUARTER_MARGIN.replace("June 28, 2025 | ", ""),
    ):
        answer = AnswerExtractor.extract(query, body)
        assert answer.exact_answer == ""
        assert answer.confidence == 0


def test_jpm_eps_distinguishes_basic_and_diluted_rows():
    body = (
        "[JPMorgan Chase & Co. (JPM) | 10-K FY2024]\n\n"
        "2024 | 2023 | 2022 | Earnings per share data | "
        "Net income: Basic | $ | 19.79 | $ | 16.25 | $ | 12.10 | "
        "Diluted | 19.75 | 16.23 | 12.09 | Weighted-average shares"
    )
    query = "What was JPMorgan's basic earnings per share in fiscal 2024?"
    assert AnswerExtractor.extract(query, body).exact_answer == (
        "Basic earnings per share - FY2024: $19.79 per share"
    )
    assert AnswerExtractor.extract(query, body.replace("2024 | 2023 | 2022 | ", "")).confidence == 0


def test_lly_total_revenue_uses_consolidated_row():
    query = "What was Eli Lilly's total revenue for fiscal 2024, in millions of dollars?"
    body = (
        "Consolidated Statements of Operations (Dollars in millions) | 2024 | 2023 | "
        "U.S. | 30,375.2 | 21,791.0 | Revenue (Note 2) | $ | 45,042.7 | $ | 34,124.1"
    )
    assert AnswerExtractor.extract(query, body).exact_answer == (
        "Total revenue - FY2024: $45,042.7 million"
    )
    assert AnswerExtractor.extract(query, body.replace("Consolidated Statements of Operations", "Regional sales")).confidence == 0


def test_vfs_deliveries_require_vehicle_recipient_and_date():
    query = "How many EVs had VinFast delivered to GSM as of December 31, 2024?"
    body = "As of December 31, 2024, we have delivered approximately 46,500 EVs and 41,650 e-scooters to GSM."
    assert AnswerExtractor.extract(query, body).exact_answer == (
        "Approximately 46,500 EVs delivered to GSM as of December 31, 2024"
    )
    assert AnswerExtractor.extract(query, body.replace("GSM", "Green Future")).confidence == 0
    assert AnswerExtractor.extract(query, body.replace("2024", "2023")).confidence == 0
