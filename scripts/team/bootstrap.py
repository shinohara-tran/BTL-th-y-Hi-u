"""Paired bootstrap confidence interval for the difference between two methods.

Example:
    python scripts/team/bootstrap.py hybrid_qp_w bm25_dense
    python scripts/team/bootstrap.py hybrid_plus hybrid_qp_w --metric ndcg@10

Reads per-query scores from evaluation/team/results/team.json (or --results), resamples the
labelled questions with replacement and reports the mean difference with a 95% interval.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS = ROOT / "evaluation" / "team" / "results" / "team.json"


def per_query(data: dict, method: str, metric: str) -> Dict[str, float]:
    rows = data["methods"][method]["per_query"]
    return {r["qid"]: r[metric] for r in rows if r.get(metric) is not None}


def bootstrap(diffs: List[float], n: int, seed: int) -> List[float]:
    rng = random.Random(seed)
    size = len(diffs)
    means = []
    for _ in range(n):
        sample = [diffs[rng.randrange(size)] for _ in range(size)]
        means.append(sum(sample) / size)
    means.sort()
    return means


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("method_a", help="Method being tested, e.g. hybrid_qp_w")
    ap.add_argument("method_b", help="Reference method, e.g. bm25_dense")
    ap.add_argument("--metric", default=None, help="mrr or ndcg@10 (default: both)")
    ap.add_argument("--results", default=str(DEFAULT_RESULTS))
    ap.add_argument("-n", type=int, default=10000, help="Bootstrap resamples")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    data = json.loads(Path(args.results).read_text(encoding="utf-8-sig"))
    metrics = [args.metric] if args.metric else ["mrr", "ndcg@10"]
    print(f"{args.method_a} - {args.method_b}  ({args.n} resamples, seed {args.seed})")
    for metric in metrics:
        a = per_query(data, args.method_a, metric)
        b = per_query(data, args.method_b, metric)
        qids = sorted(set(a) & set(b))
        diffs = [a[q] - b[q] for q in qids]
        means = bootstrap(diffs, args.n, args.seed)
        lo, hi = means[int(0.025 * args.n)], means[int(0.975 * args.n) - 1]
        mean = sum(diffs) / len(diffs)
        better = sum(1 for d in diffs if d > 1e-9)
        worse = sum(1 for d in diffs if d < -1e-9)
        verdict = "khoang tin cay khong chua 0" if lo > 0 or hi < 0 else "khoang tin cay chua 0, chua khang dinh duoc"
        print(f"  {metric:8s} chenh {mean:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]  "
              f"hon {better} / kem {worse} / hoa {len(diffs) - better - worse} tren {len(diffs)} cau  -> {verdict}")


if __name__ == "__main__":
    main()
