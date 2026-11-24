"""Unit tests for DocumentChunker."""

from hybrid_search.chunking.chunker import DocumentChunker
from hybrid_search.models.document import Document, DocumentSection


def test_chunk_document_basic(sample_document: Document):
    chunker = DocumentChunker(chunk_size_tokens=100, chunk_overlap_tokens=20)
    chunks = chunker.chunk_document(sample_document)
    assert len(chunks) >= 1
    c = chunks[0]
    assert c.document_id == sample_document.document_id
    assert c.ticker == "NVDA"
    assert c.chunk_id == f"{sample_document.document_id}_chunk_0000"
    assert c.section == "Item 1A: Risk Factors"
    assert len(c.text_hash) == 64


def test_chunking_determinism(sample_document: Document):
    chunker = DocumentChunker(chunk_size_tokens=200, chunk_overlap_tokens=50)
    chunks1 = chunker.chunk_document(sample_document)
    chunks2 = chunker.chunk_document(sample_document)

    assert len(chunks1) == len(chunks2)
    for c1, c2 in zip(chunks1, chunks2):
        assert c1.chunk_id == c2.chunk_id
        assert c1.text == c2.text
        assert c1.text_hash == c2.text_hash


def test_chunking_large_text():
    long_text = " ".join([f"Sentence number {i} provides financial disclosure on operations." for i in range(100)])
    doc = Document(
        document_id="doc_large",
        company="Large Corp",
        ticker="LRG",
        cik="0001999999",
        accession_number="0001999999-24-000001",
        document_type="10-K",
        filing_date="2024-03-01",
        report_date="2023-12-31",
        fiscal_period="FY2023",
        source_url="https://example.com",
        sections=[
            DocumentSection(section_name="Item 7: MD&A", section_code="ITEM_7", text=long_text)
        ],
    )
    chunker = DocumentChunker(chunk_size_tokens=50, chunk_overlap_tokens=10)
    chunks = chunker.chunk_document(doc)
    assert len(chunks) > 1
    assert chunks[0].chunk_id == "doc_large_chunk_0000"
    assert chunks[1].chunk_id == "doc_large_chunk_0001"


def test_chunker_token_limit_and_fact_years():
    long_financial_text = "\n".join([
        "Services net sales: 2024 = 96,169; 2023 = 85,200; 2022 = 78,129. Unit: millions of USD.",
        "iPhone net sales: 2024 = 201,183; 2023 = 200,583; 2022 = 205,489. Unit: millions of USD.",
        "Total net sales expanded across the Americas, Europe, Greater China, and Rest of Asia Pacific.",
    ] * 20)
    doc = Document(
        document_id="doc_apple_facts",
        company="Apple Inc.",
        ticker="AAPL",
        cik="0000320193",
        accession_number="0000320193-24-000106",
        document_type="10-K",
        filing_date="2024-11-01",
        report_date="2024-09-28",
        fiscal_period="FY2024",
        source_url="https://example.com/aapl",
        sections=[
            DocumentSection(section_name="Item 8: Financial Statements", section_code="ITEM_8", text=long_financial_text)
        ],
    )
    chunker = DocumentChunker(chunk_size_tokens=480, chunk_overlap_tokens=80)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) > 0
    for c in chunks:
        # Strict guarantee: header + body <= 480 tokens
        tokens = chunker.count_tokens(c.text)
        assert tokens <= 480, f"Chunk {c.chunk_id} has {tokens} tokens > 480"
        # fact_years extracted correctly
        assert 2024 in c.fact_years
        assert 2023 in c.fact_years
        assert 2022 in c.fact_years


def test_extract_fact_years_fallback():
    from hybrid_search.chunking.chunker import extract_fact_years

    # 1. Years in text take precedence
    assert extract_fact_years("Sales in 2024 were strong", fallback_period="FY2022") == [2024]

    # 2. Text has no years -> fallback to fiscal_period from Tùng's period fix
    assert extract_fact_years("General corporate risk factors and governance", fallback_period="FY2022") == [2022]
    assert extract_fact_years("Quarterly filing narrative without year", fallback_period="Q-2023-09") == [2023]
    assert extract_fact_years("VinFast business combination event", fallback_period="Event 2023-08-14") == [2023]
    assert extract_fact_years("No date narrative", fallback_period="Unknown") == []

