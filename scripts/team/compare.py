"""Gộp nhiều kết quả evaluate.py thành một bảng so sánh.

    python scripts/team/compare.py baseline part1 part2 part3 part4 team
    python scripts/team/compare.py baseline team --method rerank --out evaluation/team/results/compare.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import common
from evaluate import METRIC_KEYS, fmt


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tags", nargs="+", help="Các tag đã chạy evaluate.py")
    ap.add_argument("--results-dir", default=str(common.DEFAULT_RESULTS))
    ap.add_argument("--method", default=None, help="Chỉ so một cách tìm, ví dụ rerank")
    ap.add_argument("--out", default=None, help="Ghi bảng ra file .md")
    args = ap.parse_args()

    results = {}
    for tag in args.tags:
        p = Path(args.results_dir) / f"{tag}.json"
        if not p.exists():
            raise SystemExit(f"Không thấy {p}. Chạy evaluate.py --tag {tag} trước.")
        results[tag] = json.loads(p.read_text(encoding="utf-8"))

    splits = {r["meta"]["split"] for r in results.values()}
    nq = {r["meta"]["n_queries"] for r in results.values()}
    warn = []
    if len(splits) > 1 or len(nq) > 1:
        warn.append(f"Cảnh báo: các kết quả chạy trên bộ câu hỏi khác nhau (split {sorted(splits)}, số câu {sorted(nq)}). Không nên so trực tiếp.")

    head = ["Tag", "Method"] + METRIC_KEYS + ["p50 ms", "commit", "dense"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for tag, r in results.items():
        for m, mr in r["methods"].items():
            if args.method and m != args.method:
                continue
            s = mr["summary"]
            lines.append("| " + " | ".join(
                [tag, m] + [fmt(s[k]) for k in METRIC_KEYS]
                + [fmt(s["latency_p50_ms"]), r["meta"]["git_commit"], r["meta"]["dense_model"]]) + " |")
    text = "\n".join(warn + [""] + lines) if warn else "\n".join(lines)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"Đã lưu: {args.out}")


if __name__ == "__main__":
    main()
