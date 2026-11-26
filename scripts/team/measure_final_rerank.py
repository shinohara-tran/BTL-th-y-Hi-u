"""Compare reranker speed and direct answers on the final corpus."""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
from pathlib import Path
from statistics import median
from time import perf_counter
from unittest.mock import patch

from qdrant_client import QdrantClient

from hybrid_search.api import SearchRequest, create_app
from hybrid_search.config import load_config
from hybrid_search.retrieval.engine import SearchEngine

CASES = (
    ("aapl-services", "AAPL", "What were Apple's Services net sales in fiscal 2024?", "$96,169 million"),
    ("aapl-annual", "AAPL", "For the full fiscal year 2025, what was Apple's Products gross margin percentage?", "36.8%"),
    ("aapl-quarter", "AAPL", "For the third quarter of fiscal 2025, what was Apple's Products gross margin percentage?", "34.5%"),
    ("jpm-eps", "JPM", "What was JPMorgan Chase's basic earnings per share in fiscal 2024?", "$19.79 per share"),
    ("lly-revenue", "LLY", "What was Eli Lilly's total revenue for fiscal 2024, in millions of dollars?", "$45,042.7 million"),
    ("vfs-ev", "VFS", "How many EVs had VinFast delivered to GSM as of December 31, 2024?", "46,500 EVs delivered to GSM as of December 31, 2024"),
)
CONFIGS = ((20, 0), (10, 0), (10, 256))
CONFIDENCE_THRESHOLD = 0.30


async def run(out: Path, repeats: int) -> None:
    cfg = load_config()
    if cfg.qdrant.collection_name != "team_docs_final":
        raise ValueError("Expected collection team_docs_final")
    with_client = QdrantClient(url=cfg.qdrant.url, timeout=120)
    try:
        manifest = Path(os.environ.get("TEAM13_BUILD_MANIFEST", "data/processed/build.json"))
        expected = json.loads(manifest.read_text(encoding="utf-8"))["chunks"]
        actual = with_client.count(cfg.qdrant.collection_name, exact=True).count
        if actual != expected or expected != 14022:
            raise ValueError(f"Expected 14022 approved chunks, found {actual} (manifest {expected})")
        engine = SearchEngine(config=cfg, client=with_client)
        app = create_app(engine=engine)
        search = next(route.endpoint for route in app.routes if route.path == "/api/search")
        rows = []
        baseline = {}
        summary = []
        for candidates, tokens in CONFIGS:
            name = f"{candidates}-{'full' if not tokens else tokens}"
            engine.reranker.candidate_limit = candidates
            engine.reranker.max_passage_tokens = tokens
            print(f"{name}: warm-up...", flush=True)
            _, ticker, query, _ = CASES[0]
            await search(SearchRequest(query=query, method="rerank", tickers=[ticker], k=5))
            measured = []
            for run_number in range(1, repeats + 1):
                for case, ticker, query, value in CASES:
                    observed = []
                    original_search = engine.search

                    def capture(*args, **kwargs):
                        results = original_search(*args, **kwargs)
                        observed.extend(results)
                        return results

                    request = SearchRequest(query=query, method="rerank", tickers=[ticker], k=5)
                    start = perf_counter()
                    with patch.object(engine, "search", side_effect=capture):
                        response = await search(request)
                    elapsed = round((perf_counter() - start) * 1000, 2)
                    direct = response.get("direct_answer") or {}
                    matched = [
                        result for result in observed
                        if result.ticker == ticker and " ".join(result.exact_answer.split()).endswith(value)
                    ]
                    correct = f"({ticker})" in direct.get("source", "") and " ".join(
                        direct.get("exact_answer", "").split()
                    ).endswith(value)
                    hidden = bool(matched) and not correct and all(
                        r.answer_confidence < CONFIDENCE_THRESHOLD for r in matched
                    )
                    ranks = [result.chunk_id for result in observed]
                    key = (run_number, case)
                    if name == "20-full":
                        baseline[key] = ranks
                    row = {
                        "configuration": name, "trial": run_number, "case": case,
                        "elapsed_ms": elapsed, "answer": direct.get("exact_answer"),
                        "correct": correct, "hidden_by_confidence": hidden,
                        "correct_candidate_confidence": [r.answer_confidence for r in matched],
                        "same_top5_as_20_full": baseline[key] == ranks,
                    }
                    rows.append(row)
                    measured.append(row)
                    print(f"{name} {run_number}/{repeats} {case}: {elapsed:.0f}ms correct={correct} hidden={hidden}", flush=True)
            times = sorted(row["elapsed_ms"] for row in measured)
            summary.append({
                "configuration": name, "samples": len(times), "p50_ms": round(median(times), 2),
                "p95_ms": times[math.ceil(0.95 * len(times)) - 1],
                "correct": sum(row["correct"] for row in measured),
                "hidden_by_confidence": sum(row["hidden_by_confidence"] for row in measured),
                "same_top5_as_20_full": sum(row["same_top5_as_20_full"] for row in measured),
            })
        report = {"collection": cfg.qdrant.collection_name, "chunks": actual, "summary": summary, "per_query": rows}
        out.parent.mkdir(parents=True, exist_ok=True)
        temp = out.with_suffix(".tmp")
        temp.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp.replace(out)
        print(json.dumps(summary, indent=2))
        print(f"Saved {out}")
    finally:
        with_client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--out", type=Path, default=Path("evaluation/team/results/part4_final_demo.json"))
    opts = parser.parse_args()
    if opts.repeats < 1:
        parser.error("--repeats must be positive")
    asyncio.run(run(opts.out, opts.repeats))


if __name__ == "__main__":
    main()
