"""Unit tests for configuration loader."""

from hybrid_search.config import load_config


def test_load_default_config():
    config = load_config()
    assert config.edgar.rate_limit_per_second == 8.0
    assert config.chunking.chunk_size_tokens in [480, 500]
    assert config.embeddings.dense_model == "BAAI/bge-small-en-v1.5"
    assert config.embeddings.bm25_model == "Qdrant/bm25"
    assert config.embeddings.sparse_model == "prithivida/Splade_PP_en_v1"
    # Team dataset (config/companies.yaml); upstream list is kept in companies_original.yaml
    assert config.qdrant.collection_name in ["team_docs", "financial_docs", "team_docs_p1", "team_docs_final"]
    tickers = [c.ticker for c in config.companies]
    assert len(tickers) == 13
    assert {"NVDA", "AAPL", "TSM", "VFS", "LLY", "JPM"} <= set(tickers)

    vfs = next(c for c in config.companies if c.ticker == "VFS")
    assert vfs.cik == "0001913510"
    assert vfs.forms == ["20-F"]


def test_env_overrides_companies_and_collection(monkeypatch):
    monkeypatch.setenv("HYBRID_COMPANIES_FILE", "config/companies_new3.yaml")
    monkeypatch.setenv("QDRANT_COLLECTION", "team_docs_part2")
    config = load_config()
    assert [c.ticker for c in config.companies] == ["VFS", "LLY", "JPM"]
    assert config.qdrant.collection_name == "team_docs_part2"
