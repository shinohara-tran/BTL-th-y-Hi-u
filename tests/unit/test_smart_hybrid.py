"""Phần 3: query understanding, weighted RRF and near-duplicate removal (no models or Qdrant needed)."""

from types import SimpleNamespace

import pytest

from hybrid_search.config import RetrievalConfig, load_config
from hybrid_search.models.filter import MetadataFilter
from hybrid_search.models.search import SearchResult
from hybrid_search.retrieval.query_parser import QueryParser, classify, short_name
from hybrid_search.retrieval.smart_hybrid import SmartHybridRetriever, drop_near_duplicates, weighted_rrf


@pytest.fixture(scope="module")
def parser():
    return QueryParser(load_config().companies)


# ---------- query parser ----------

def test_short_name():
    assert short_name("Apple Inc.") == "apple"
    assert short_name("JPMorgan Chase & Co.") == "jpmorgan chase"
    assert short_name("Taiwan Semiconductor Manufacturing Co. Ltd.") == "taiwan semiconductor manufacturing"
    assert short_name("VinFast Auto Ltd.") == "vinfast"
    assert short_name("Eli Lilly and Company") == "eli lilly"


def test_company_becomes_filter_and_leaves_the_text(parser):
    p = parser.parse("How does Microsoft describe risks from AI regulation?")
    assert p.tickers == ["MSFT"]
    assert p.text == "How does the company describe risks from AI regulation?"
    assert "microsoft" not in p.text.lower()


def test_aliases_tickers_and_possessive(parser):
    assert parser.parse("Google's cloud revenue growth").tickers == ["GOOGL"]
    assert parser.parse("NVDA data center revenue").tickers == ["NVDA"]
    assert parser.parse("Eli Lilly and JPMorgan views on AI").tickers == ["LLY", "JPM"]
    assert parser.parse("TSMC advanced node capacity").tickers == ["TSM"]


def test_several_subjects_are_dropped(parser):
    p = parser.parse("Compare how Eli Lilly and JPMorgan describe risks from artificial intelligence")
    assert p.tickers == ["LLY", "JPM"]
    assert p.text == "Compare how describe risks from artificial intelligence"


def test_possessive_keeps_meaning(parser):
    assert parser.parse("Microsoft's AI risks").text == "the company's AI risks"


def test_lowercase_common_words_are_not_tickers(parser):
    p = parser.parse("meta data and amd ratios in intelligence reports")
    assert "META" not in p.tickers and "AMD" not in p.tickers and "INTC" not in p.tickers


def test_competitor_is_context_not_filter(parser):
    p = parser.parse("How does VinFast describe competition from Tesla?")
    assert p.tickers == ["VFS"]
    assert p.context_tickers == ["TSLA"]
    assert "Tesla" in p.text  # still part of what we search for


def test_forms_are_filters_years_stay_in_text(parser):
    p = parser.parse("Apple services revenue 2024 10-K")
    assert p.tickers == ["AAPL"] and p.document_types == ["10-K"]
    assert "2024" in p.text and "10-K" not in p.text


def test_name_only_query_is_kept(parser):
    p = parser.parse("Tesla")
    assert p.tickers == ["TSLA"] and p.text == "Tesla"


def test_no_company_no_filter(parser):
    p = parser.parse("exposure to changes in interest rates")
    assert p.tickers == [] and p.merge_into(None) is None


def test_user_filter_wins(parser):
    p = parser.parse("Apple risk factors")
    merged = p.merge_into(MetadataFilter(tickers=["MSFT"]))
    assert merged.tickers == ["MSFT"]


def test_classify():
    assert classify("ASC 606 revenue recognition") == "code"
    assert classify("MI300 accelerator") == "code"
    assert classify("CET1 ratio") == "code"
    assert classify("340B Drug Pricing Program") == "code"
    assert classify("revenue in 2024") == "balanced"
    assert classify("Services revenue FY2024 Q3") == "balanced"
    assert classify("how could higher deposit costs reduce the profit the bank makes on loans") == "concept"


# ---------- fusion and dedup ----------

def res(cid: str, text: str = "x") -> SearchResult:
    return SearchResult(chunk_id=cid, document_id="d", score=0.0, rank=0, text=text, company="C", ticker="T",
                        document_type="10-K", filing_date="", fiscal_period="", section="", sector="",
                        geography="", source_url="", retrieval_method="")


def test_weighted_rrf_follows_weights():
    lex = [res("a"), res("b")]
    sem = [res("b"), res("c")]
    assert [r.chunk_id for r in weighted_rrf([lex, sem], [0.5, 0.5])][0] == "b"
    assert [r.chunk_id for r in weighted_rrf([[res("a")], [res("c")]], [0.9, 0.1])] == ["a", "c"]
    assert [r.chunk_id for r in weighted_rrf([[res("a")], [res("c")]], [0.1, 0.9])] == ["c", "a"]


def test_drop_near_duplicates():
    rs = [res("a"), res("b"), res("c"), res("d")]
    vecs = {"a": [1, 0], "b": [0.999, 0.01], "c": [0, 1]}  # b repeats a; d has no vector
    assert [r.chunk_id for r in drop_near_duplicates(rs, vecs, 0.95)] == ["a", "c", "d"]


def test_drop_repeated_answer_sentence():
    sentence = "We maintain a long-term strategic partnership with OpenAI originally established in 2019."
    rs = [res("10k"), res("10q"), res("other"), res("short1"), res("short2")]
    rs[0].exact_answer = sentence
    rs[1].exact_answer = "  " + sentence.upper() + " "  # same sentence, different chunk around it
    rs[2].exact_answer = "Competition in cloud services could reduce our margins and revenue growth."
    rs[3].exact_answer = rs[4].exact_answer = "Revenue grew."  # too short to judge
    vecs = {"10k": [1, 0], "10q": [0, 1], "other": [0.7, 0.7]}  # vectors alone would keep all
    assert [r.chunk_id for r in drop_near_duplicates(rs, vecs, 0.95)] == ["10k", "other", "short1", "short2"]


def test_drop_reworded_answer_sentence():
    rs = [res("10k"), res("10q"), res("rule"), res("law")]
    rs[0].exact_answer = "Microsoft and OpenAI maintain a long-term strategic partnership originally established in 2019."
    rs[1].exact_answer = ('Microsoft and OpenAI Global, LLC ("OpenAI") maintain a long-term strategic partnership '
                          "originally established in 2019.")
    rs[2].exact_answer = ("The potential replacement of the recently rescinded AI Diffusion Rule and other potential "
                          "AI-related rulemakings could adversely affect Microsoft's business.")
    rs[3].exact_answer = ("Governments are actively enforcing competition laws and regulations and enacting new "
                          "regulations to intervene in digital markets.")
    assert [r.chunk_id for r in drop_near_duplicates(rs, {}, 0.95)] == ["10k", "rule", "law"]


class StubRetriever:
    def __init__(self, ids):
        self.ids, self.calls = ids, []

    def search(self, query, k=10, filters=None, prefetch_k=50):
        self.calls.append((query, filters))
        return [res(i) for i in self.ids[:k]]


class StubClient:
    def scroll(self, **kwargs):
        pts = [SimpleNamespace(id=i, payload={"chunk_id": cid}, vector={"dense": v})
               for i, (cid, v) in enumerate({"a": [1, 0], "b": [1, 0.001], "c": [0, 1]}.items())]
        return pts, None


def make(mode, parser):
    bm25, dense, server = StubRetriever(["a", "b"]), StubRetriever(["b", "c"]), StubRetriever(["s1"])
    r = SmartHybridRetriever(StubClient(), "col", parser, bm25, dense, server, RetrievalConfig(), mode)
    return r, bm25, dense, server


def test_smart_modes(parser):
    r, bm25, dense, server = make("hybrid_qp", parser)
    out = r.search("How does Microsoft describe AI risks?", k=5)
    assert [x.chunk_id for x in out] == ["s1"]
    q, f = server.calls[0]
    assert "Microsoft" not in q and f.tickers == ["MSFT"]
    assert out[0].retrieval_method == "hybrid_qp"

    r, bm25, dense, _ = make("hybrid_qp_w", parser)
    assert [x.chunk_id for x in r.search("AI risks", k=5)] == ["b", "a", "c"]

    r, *_ = make("hybrid_plus", parser)
    assert [x.chunk_id for x in r.search("AI risks", k=5)] == ["b", "c"]  # a dropped: same vector as b


def test_unknown_mode_rejected(parser):
    with pytest.raises(ValueError):
        SmartHybridRetriever(None, "c", parser, None, None, None, RetrievalConfig(), "nope")
