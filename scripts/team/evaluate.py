"""Chấm điểm một cấu hình trên bộ câu hỏi chung của nhóm.

Mỗi lần chạy ghi ra 2 file trong evaluation/team/results/:
  <tag>.json  để script compare.py gộp bảng
  <tag>.md    để đọc nhanh hoặc dán vào báo cáo

    python scripts/team/evaluate.py --tag baseline
    python scripts/team/evaluate.py --tag part3 --methods bm25_dense rerank --split dev

Quy ước đặt tag: baseline, part1, part2, part3, part4, team, team-no-part2 ...
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence

import common
from hybrid_search.evaluation import team_metrics as tm

METRIC_KEYS = ["mrr", "ndcg@10", "recall@10", "p@10", "company@5", "dup@5", "unjudged@10"]


def evaluate(engine, queries: Sequence[dict], qrels: Dict[str, Dict[str, int]],
             methods: Sequence[str], k: int = 10) -> dict:
    per_method = {}
    for method in methods:
        per_query, latencies = [], []
        for q in queries:
            t0 = time.perf_counter()
            hits = engine.search(query=q["query"], method=method, k=k)
            latencies.append((time.perf_counter() - t0) * 1000)
            ids = [h.chunk_id for h in hits]
            judged = qrels.get(q["id"], {})
            has_labels = bool(judged)
            per_query.append({
                "qid": q["id"],
                "category": q["category"],
                "mrr": tm.mrr(ids, judged, k) if has_labels else None,
                "ndcg@10": tm.ndcg(ids, judged, 10) if has_labels else None,
                "recall@10": tm.recall(ids, judged, 10) if has_labels else None,
                "p@10": tm.precision(ids, judged, 10) if has_labels else None,
                "company@5": tm.company_accuracy([h.ticker for h in hits], q.get("expected_tickers", []), 5),
                "dup@5": tm.duplicate_rate([h.text for h in hits], 5),
                "unjudged@10": tm.unjudged_rate(ids, judged, 10) if has_labels else None,
                "top5": [f"{h.ticker}|{h.document_type}|{h.fiscal_period}|{h.chunk_id}" for h in hits[:5]],
            })
        summary = {key: tm.mean([r[key] for r in per_query]) for key in METRIC_KEYS}
        summary["latency_p50_ms"] = tm.percentile(latencies, 50)
        summary["latency_p95_ms"] = tm.percentile(latencies, 95)
        summary["n_queries_labeled"] = sum(1 for r in per_query if r["mrr"] is not None)
        by_cat = {}
        for cat in sorted({r["category"] for r in per_query}):
            rows = [r for r in per_query if r["category"] == cat]
            by_cat[cat] = {key: tm.mean([r[key] for r in rows]) for key in ("mrr", "ndcg@10", "company@5", "dup@5")}
            by_cat[cat]["n"] = len(rows)
        per_method[method] = {"summary": summary, "by_category": by_cat, "per_query": per_query}
    return per_method


def fmt(v) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.1f}" if v >= 10 else f"{v:.3f}"
    return str(v)


def to_markdown(result: dict) -> str:
    meta = result["meta"]
    lines = [f"# Kết quả: {meta['tag']}", ""]
    for key in ("timestamp", "git_commit", "split", "n_queries", "n_points", "dense_model", "sparse_model",
                "bm25_model", "collection", "machine"):
        lines.append(f"- **{key}**: {meta.get(key)}")
    lines += ["", "## Tổng hợp", "",
              "| Method | " + " | ".join(METRIC_KEYS) + " | p50 ms | p95 ms |",
              "|---|" + "---|" * (len(METRIC_KEYS) + 2)]
    for m, r in result["methods"].items():
        s = r["summary"]
        lines.append(f"| {m} | " + " | ".join(fmt(s[k]) for k in METRIC_KEYS)
                     + f" | {fmt(s['latency_p50_ms'])} | {fmt(s['latency_p95_ms'])} |")
    lines += ["", "## Theo nhóm câu hỏi (NDCG@10)", ""]
    cats = sorted({c for r in result["methods"].values() for c in r["by_category"]})
    lines.append("| Method | " + " | ".join(cats) + " |")
    lines.append("|---|" + "---|" * len(cats))
    for m, r in result["methods"].items():
        lines.append(f"| {m} | " + " | ".join(fmt(r["by_category"].get(c, {}).get("ndcg@10")) for c in cats) + " |")
    lines += ["", "Ghi chú: unjudged@10 cao (trên 0,2) nghĩa là cấu hình này tìm ra nhiều chunk chưa ai chấm. "
              "Chạy lại pool.py, chấm thêm, rồi chạy lại evaluate.py.", ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", required=True, help="Tên cấu hình, ví dụ baseline, part2, team")
    ap.add_argument("--queries", default=str(common.DEFAULT_QUERIES))
    ap.add_argument("--labels", default=str(common.DEFAULT_LABELS))
    ap.add_argument("--out-dir", default=str(common.DEFAULT_RESULTS))
    ap.add_argument("--methods", nargs="*", default=None, help="Mặc định: tất cả cách tìm của engine")
    ap.add_argument("--split", default="all", choices=["all", "dev", "test"])
    ap.add_argument("--force", action="store_true", help="Cho phép ghi đè kết quả có cùng tag")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    json_path, md_path = out_dir / f"{args.tag}.json", out_dir / f"{args.tag}.md"
    if json_path.exists() and not args.force:
        raise SystemExit(f"{json_path} đã có. Đổi --tag hoặc thêm --force nếu chắc chắn muốn ghi đè.")

    queries = common.load_queries(Path(args.queries), args.split)
    qrels = common.load_qrels(Path(args.labels))
    engine, config = common.build_engine()
    methods = args.methods or engine.METHOD_NAMES
    try:
        n_points = engine.client.count(engine.collection_name).count
    except Exception:
        n_points = None

    result = {
        "meta": {
            "tag": args.tag,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "git_commit": common.git_commit(),
            "split": args.split,
            "n_queries": len(queries),
            "n_points": n_points,
            "collection": engine.collection_name,
            "dense_model": config.embeddings.dense_model,
            "sparse_model": config.embeddings.sparse_model,
            "bm25_model": config.embeddings.bm25_model,
            "rrf_constant": config.retrieval.rrf_constant,
            "machine": f"{platform.system()} {platform.machine()}, Python {platform.python_version()}",
        },
        "methods": evaluate(engine, queries, qrels, methods),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(to_markdown(result), encoding="utf-8")
    print(to_markdown(result))
    print(f"Đã lưu: {json_path} và {md_path}")


if __name__ == "__main__":
    main()
