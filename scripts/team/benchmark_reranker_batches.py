"""Measure reranker batch sizes against the same live retrieval candidates."""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from collections import Counter
import time
from pathlib import Path
from urllib.request import Request, urlopen

CASES = {
    "AAPL": "For the third quarter of fiscal 2025, what was Apple's Products gross margin percentage?",
    "JPM": "What was JPMorgan Chase's basic earnings per share in fiscal 2024?",
    "LLY": "What was Eli Lilly's total revenue for fiscal 2024, in millions of dollars?",
    "VFS": "Approximately how many EVs had VinFast delivered to GSM as of December 31, 2024?",
}
BATCH_SIZES = (2, 8, 16)


def fetch_candidates(url: str) -> dict:
    cases = {}
    for ticker, query in CASES.items():
        print(f"Fetching 20 candidates for {ticker}...", file=sys.stderr, flush=True)
        body = json.dumps({
            "query": query, "method": "sparse_dense", "tickers": [ticker],
            "form_types": ["10-K", "10-Q", "20-F"], "k": 20,
        }).encode()
        request = Request(f"{url}/api/search", data=body, headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=180) as response:
            results = json.load(response)["results"]
        texts = [result["full_text"] for result in results]
        if not texts:
            raise RuntimeError(f"No candidates returned for {ticker}")
        cases[ticker] = (query, texts)
    return cases


def candidates_from_chunks(path: Path) -> dict:
    """Select fixed representative inputs without starting the search API."""
    query_words = {
        ticker: set(re.findall(r"[a-z0-9]+", query.lower()))
        for ticker, query in CASES.items()
    }
    ranked = {ticker: [] for ticker in CASES}
    with path.open(encoding="utf-8-sig") as rows:
        for line in rows:
            if not line.strip():
                continue
            chunk = json.loads(line)
            ticker = chunk["ticker"]
            if ticker not in ranked:
                continue
            counts = Counter(re.findall(r"[a-z0-9]+", chunk["text"].lower()))
            score = sum(math.log1p(counts[word]) for word in query_words[ticker] if len(word) > 3)
            ranked[ticker].append((-score, chunk["chunk_id"], chunk["text"]))
    cases = {}
    for ticker, query in CASES.items():
        candidates = sorted(ranked[ticker])[:20]
        if len(candidates) != 20:
            raise RuntimeError(f"Expected 20 chunks for {ticker}, got {len(candidates)}")
        cases[ticker] = (query, [text for _, _, text in candidates])
    return cases


def benchmark(cases: dict, repeats: int, cache_dir: str | None = None) -> dict:
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    print("Loading the cached reranker model...", file=sys.stderr, flush=True)
    start = time.perf_counter()
    model = TextCrossEncoder(model_name="BAAI/bge-reranker-base", cache_dir=cache_dir, local_files_only=True)
    load_ms = round((time.perf_counter() - start) * 1000, 2)
    durations = {size: [] for size in BATCH_SIZES}
    rankings = {}
    total_runs = len(cases) * len(BATCH_SIZES) * (repeats + 1)
    completed = 0
    for ticker, (query, texts) in cases.items():
        for size in BATCH_SIZES:
            list(model.rerank(query, texts, batch_size=size))
            completed += 1
            print(f"[{completed}/{total_runs}] {ticker} batch {size} warm-up done",
                  file=sys.stderr, flush=True)
        for repetition in range(repeats):
            offset = repetition % len(BATCH_SIZES)
            for size in BATCH_SIZES[offset:] + BATCH_SIZES[:offset]:
                start = time.perf_counter()
                scores = list(model.rerank(query, texts, batch_size=size))
                durations[size].append((time.perf_counter() - start) * 1000)
                if len(scores) != len(texts):
                    raise RuntimeError(f"Expected {len(texts)} scores, got {len(scores)}")
                order = sorted(range(len(scores)), key=scores.__getitem__, reverse=True)
                rankings[ticker, repetition, size] = order[:5]
                completed += 1
                print(f"[{completed}/{total_runs}] {ticker} batch {size}: {durations[size][-1]:.0f} ms",
                      file=sys.stderr, flush=True)

    report = {
        "model": "BAAI/bge-reranker-base",
        "model_load_ms": load_ms,
        "candidate_counts": {ticker: len(texts) for ticker, (_, texts) in cases.items()},
        "repeats": repeats,
        "batches": [],
    }
    for size, times in durations.items():
        p95 = sorted(times)[math.ceil(0.95 * len(times)) - 1]
        agreements = sum(
            rankings[ticker, trial, size] == rankings[ticker, trial, 2]
            for ticker in cases for trial in range(repeats)
        )
        report["batches"].append({
            "batch_size": size, "samples": len(times),
            "p50_ms": round(statistics.median(times), 2), "p95_ms": round(p95, 2),
            "top5_exact_matches_vs_batch_2": agreements,
            "latencies_ms": [round(value, 2) for value in times],
        })
    try:
        import resource
        report["process_peak_rss_mib"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2)
    except ImportError:
        pass
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--candidates-only", action="store_true")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--save-candidates", type=Path)
    source.add_argument("--load-candidates", type=Path)
    parser.add_argument("--chunks", type=Path, help="Read candidate inputs from local chunks.jsonl")
    parser.add_argument("--cache-dir")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    if args.load_candidates:
        cases = json.loads(args.load_candidates.read_text(encoding="utf-8"))
    elif args.chunks:
        cases = candidates_from_chunks(args.chunks)
    else:
        cases = fetch_candidates(args.url.rstrip("/"))
    if args.save_candidates:
        args.save_candidates.write_text(json.dumps(cases), encoding="utf-8")
        return
    if args.candidates_only:
        result = {ticker: len(texts) for ticker, (_, texts) in cases.items()}
    else:
        result = benchmark(cases, args.repeats, args.cache_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
