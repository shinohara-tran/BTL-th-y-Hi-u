"""FastAPI REST API Server for Financial Hybrid Search Web UI."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from hybrid_search.config import AppConfig, get_project_root, load_config
from hybrid_search.evaluation.benchmark import BenchmarkRunner
from hybrid_search.models.filter import MetadataFilter
from hybrid_search.retrieval.engine import SearchEngine
from hybrid_search.retrieval.extractor import AnswerExtractor


# Request Models
class SearchRequest(BaseModel):
    query: str
    method: str = "sparse_dense"
    tickers: Optional[List[str]] = None
    form_types: Optional[List[str]] = None
    section_types: Optional[List[str]] = None
    filing_date_start: Optional[str] = None
    filing_date_end: Optional[str] = None
    k: int = Field(default=5, ge=1, le=50)


class BenchmarkRequest(BaseModel):
    k: int = Field(default=10, ge=1, le=50)
    category_filter: Optional[str] = None
    fast_mode: bool = True


_lazy_engine: Optional[SearchEngine] = None


def get_default_engine() -> SearchEngine:
    """Lazily initialize global SearchEngine instance on first actual query."""
    global _lazy_engine
    if _lazy_engine is None:
        # Team fix: read config/default.yaml like the CLI does (AppConfig() ignored the YAML).
        _lazy_engine = SearchEngine(config=load_config())
    return _lazy_engine


def create_app(engine: Optional[SearchEngine] = None) -> FastAPI:
    app = FastAPI(
        title="Financial Hybrid Search API",
        description="REST backend for Financial Intelligence Hybrid Search with Qdrant and Neural Reranking",
        version="0.1.0",
    )

    # CORS configuration for local browser and cross-origin access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _get_engine() -> SearchEngine:
        return engine if engine is not None else get_default_engine()

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return Response(status_code=204)

    @app.get("/api/status")
    async def get_status() -> Dict[str, Any]:
        """Returns Qdrant vector database connection status and collection stats."""
        eng = _get_engine()
        try:
            coll_info = eng.client.get_collection(eng.collection_name)
            # Team fix: report the real count (upstream clamped it to >= 8,609).
            points_count = getattr(coll_info, "points_count", None) or 0
            status_val = getattr(coll_info, "status", "green")
        except Exception:
            points_count = 0
            status_val = "unavailable"

        storage_mode = "embedded"
        if hasattr(eng.client, "_client"):
            client_type = str(type(eng.client._client)).lower()
            if "remote" in client_type or "http" in client_type:
                storage_mode = "server"

        return {
            "status": "online",
            "collection": eng.collection_name,
            "points_count": points_count,
            "dense_model": eng.config.embeddings.dense_model,
            "bm25_model": eng.config.embeddings.bm25_model,
            "sparse_model": eng.config.embeddings.sparse_model,
            "reranker": "Neural Cross-Encoder + Tabular Extractor",
            "storage_mode": storage_mode,
        }

    @app.get("/api/metadata")
    async def get_metadata() -> Dict[str, Any]:
        """Returns available tickers, form types, SEC item definitions, and retrieval methods."""
        return {
            # Team fix: build the company list from config/companies.yaml instead of the hardcoded 10 tickers.
            "tickers": [
                {"ticker": c.ticker, "name": c.name, "cik": c.cik, "sector": c.sector, "fy_end": "", "form": ", ".join(c.forms)}
                for c in load_config().companies
            ],
            "form_types": ["10-K", "10-Q", "20-F"],
            "sec_filing_items": {
                "10-K": [
                    {"item": "Item 1", "title": "Business", "desc": "Company operations, product segments, subsidiaries, competitive factors, and global supply chain."},
                    {"item": "Item 1A", "title": "Risk Factors", "desc": "Material investment, operational, supply chain, macroeconomic, and regulatory risk exposures."},
                    {"item": "Item 1B", "title": "Unresolved Staff Comments", "desc": "Outstanding written comments received from SEC staff regarding previous filings."},
                    {"item": "Item 1C", "title": "Cybersecurity", "desc": "Cybersecurity risk management, strategy, governance, and board oversight disclosures."},
                    {"item": "Item 2", "title": "Properties", "desc": "Principal physical properties, manufacturing fab nodes, data centers, and corporate facilities."},
                    {"item": "Item 3", "title": "Legal Proceedings", "desc": "Material pending legal proceedings, antitrust actions, FTC inquiries, and patent disputes."},
                    {"item": "Item 7", "title": "Management's Discussion & Analysis (MD&A)", "desc": "Financial condition, capital allocation, segment gross margins, and results of operations."},
                    {"item": "Item 7A", "title": "Market Risk Disclosures", "desc": "Quantitative and qualitative disclosures about interest rate, foreign exchange, and equity risks."},
                    {"item": "Item 8", "title": "Financial Statements & Notes", "desc": "Audited balance sheets, statements of income/cash flows, footnote policies (ASC 606 revenue recognition)."},
                    {"item": "Item 9A", "title": "Controls & Procedures", "desc": "Evaluation of disclosure controls and internal control over financial reporting (ICFR)."}
                ],
                "10-Q": [
                    {"item": "Part I Item 1", "title": "Financial Statements & Condensed Notes", "desc": "Unaudited quarterly balance sheets, income statements, segment breakdowns, and footnote updates."},
                    {"item": "Part I Item 2", "title": "Management's Discussion & Analysis", "desc": "Quarterly comparative operational performance, liquidity, capex, and segment growth commentary."},
                    {"item": "Part I Item 3", "title": "Quantitative & Qualitative Market Risk", "desc": "Quarterly sensitivity analysis on foreign exchange, interest rates, and commodity fluctuations."},
                    {"item": "Part II Item 1A", "title": "Risk Factors", "desc": "Material updates or new risk factors arising since the preceding annual 10-K filing."}
                ],
                "20-F": [
                    {"item": "Item 3", "title": "Key Information & Risk Factors", "desc": "Selected financial data, capitalization, foreign exchange rates, and geopolitical risk factors."},
                    {"item": "Item 4", "title": "Information on the Company", "desc": "Organizational structure, foundry manufacturing capacity, fabrication cleanrooms, and capex."},
                    {"item": "Item 5", "title": "Operating & Financial Review", "desc": "Foreign private issuer MD&A equivalent detailing revenue drivers, node adoption (e.g. 3nm), and gross margins."},
                    {"item": "Item 18", "title": "Financial Statements & Notes", "desc": "Audited IFRS / US-GAAP reconciled consolidated financial statements and accounting schedules."}
                ]
            },
            "methods": [
                {"id": "rerank", "name": "Stage-2 Reranker", "desc": "Cross-Encoder scoring, temporal alignment & table extractor"},
                {"id": "sparse_dense", "name": "Sparse + Dense", "desc": "Learned SPLADE + Dense Hybrid Candidate Generator"},
                {"id": "bm25_dense", "name": "BM25 + Dense", "desc": "Server-side Reciprocal Rank Fusion of BM25 and Dense"},
                {"id": "sparse", "name": "Sparse (SPLADE)", "desc": "Learned sparse expansion for technical vocabulary"},
                {"id": "bm25", "name": "BM25 (Pure Lexical)", "desc": "Sparse lexical matching with server-side IDF"},
                {"id": "dense", "name": "Dense (BGE-Small)", "desc": "384d semantic vector search via Cosine distance"},
            ],
        }

    @app.post("/api/search")
    async def search(req: SearchRequest) -> Dict[str, Any]:
        """Executes search with a single configuration or compares all configurations."""
        eng = _get_engine()
        filters = MetadataFilter(
            tickers=req.tickers if req.tickers else None,
            document_types=req.form_types if req.form_types else None,
            sections=req.section_types if req.section_types else None,
            filing_date_start=req.filing_date_start if req.filing_date_start else None,
            filing_date_end=req.filing_date_end if req.filing_date_end else None,
        )

        t_start = time.perf_counter()

        if req.method == "compare_all":
            all_res = eng.search_all_configurations(
                query=req.query,
                k=req.k,
                filters=filters,
            )
            total_latency = (time.perf_counter() - t_start) * 1000

            comparisons = {}
            for m_name, res_list in all_res.items():
                items = []
                for idx, r in enumerate(res_list):
                    chunk_text = r.text
                    extracted_answer = r.exact_answer
                    highlighted_text = r.highlighted_text
                    confidence = r.answer_confidence

                    if not extracted_answer:
                        ext = AnswerExtractor.extract(req.query, chunk_text, company=r.company, ticker=r.ticker)
                        extracted_answer = ext.exact_answer
                        highlighted_text = ext.highlighted_text
                        confidence = ext.confidence

                    items.append({
                        "rank": idx + 1,
                        "score": round(r.score, 4),
                        "ticker": r.ticker,
                        "company_name": r.company,
                        "form_type": r.document_type,
                        "fiscal_year": r.fiscal_period,
                        "fact_years": getattr(r, "fact_years", []),
                        "section_title": r.section,
                        "excerpt": extracted_answer if extracted_answer else chunk_text[:240] + "...",
                        "exact_answer": extracted_answer,
                        "full_text": chunk_text,
                        "highlighted_text": highlighted_text or chunk_text,
                        "is_table_row": (" | " in (extracted_answer or "") or "Unit:" in (extracted_answer or "") or " = " in (extracted_answer or "")),
                    })
                comparisons[m_name] = items

            return {
                "query": req.query,
                "method": "compare_all",
                "latency_ms": round(total_latency, 2),
                "comparisons": comparisons,
            }

        # Single configuration execution
        results = eng.search(
            query=req.query,
            method=req.method,
            k=req.k,
            filters=filters,
        )
        latency_ms = (time.perf_counter() - t_start) * 1000

        items = []
        top_extracted = None

        for idx, r in enumerate(results):
            chunk_text = r.text
            extracted_answer = r.exact_answer
            highlighted_text = r.highlighted_text
            confidence = r.answer_confidence

            is_tbl = any(marker in extracted_answer for marker in (" | ", "Unit:", " = "))
            if not extracted_answer:
                ext = AnswerExtractor.extract(req.query, chunk_text, company=r.company, ticker=r.ticker)
                extracted_answer = ext.exact_answer
                highlighted_text = ext.highlighted_text
                confidence = ext.confidence
                is_tbl = ext.is_table_row

            if top_extracted is None and extracted_answer and confidence >= 0.3:
                top_extracted = {
                    "exact_answer": extracted_answer,
                    "confidence": confidence,
                    "is_table_row": is_tbl,
                    "source": f"{r.company} ({r.ticker}) - {r.document_type} ({r.fiscal_period})",
                    "section": r.section,
                    "score": round(r.score, 4),
                }

            items.append({
                "rank": idx + 1,
                "score": round(r.score, 4),
                "ticker": r.ticker,
                "company_name": r.company,
                "form_type": r.document_type,
                "fiscal_year": r.fiscal_period,
                "fact_years": getattr(r, "fact_years", []),
                "section_title": r.section,
                "excerpt": extracted_answer if extracted_answer else chunk_text[:240] + "...",
                "exact_answer": extracted_answer,
                "full_text": chunk_text,
                "highlighted_text": highlighted_text or chunk_text,
                "is_table_row": is_tbl,
            })

        return {
            "query": req.query,
            "method": req.method,
            "latency_ms": round(latency_ms, 2),
            "direct_answer": top_extracted,
            "results": items,
        }

    @app.post("/api/benchmark")
    async def run_benchmark(req: BenchmarkRequest) -> Dict[str, Any]:
        """Return the team's official evaluation (evaluation/team/results/team.json).

        Team fix: upstream returned a hard-coded matrix (MRR 1.0 on 8,609 chunks) that was never
        measured. This endpoint now serves the numbers produced by scripts/team/evaluate.py.
        """
        import json

        results_path = get_project_root() / "evaluation" / "team" / "results" / "team.json"
        if not results_path.exists():
            raise HTTPException(status_code=404, detail=f"{results_path} not found; run scripts/team/evaluate.py")
        data = json.loads(results_path.read_text(encoding="utf-8-sig"))
        meta = data.get("meta", {})
        metrics = []
        for method, entry in data.get("methods", {}).items():
            summary = entry.get("summary", {})
            metrics.append({
                "method": method,
                "mrr": summary.get("mrr"),
                "ndcg_at_10": summary.get("ndcg@10"),
                "recall_at_10": summary.get("recall@10"),
                "company_at_5": summary.get("company@5"),
                "dup_at_5": summary.get("dup@5"),
                "latency_p50_ms": summary.get("latency_p50_ms"),
            })
        metrics.sort(key=lambda m: m["mrr"] or 0.0, reverse=True)
        return {
            "summary": {
                "source": "evaluation/team/results/team.json",
                "n_queries": meta.get("n_queries"),
                "corpus_chunks": meta.get("n_points"),
                "collection": meta.get("collection"),
                "timestamp": meta.get("timestamp"),
                "machine": meta.get("machine"),
                "total_configurations": len(metrics),
            },
            "metrics": metrics,
        }

    # Static file serving
    root_dir = get_project_root()
    index_file = root_dir / "index.html"

    @app.get("/", response_class=HTMLResponse)
    async def serve_index():
        if index_file.exists():
            return FileResponse(index_file)
        return HTMLResponse("<h1>Financial Hybrid Search API</h1><p>index.html not found in project root.</p>")

    return app


app = create_app()
