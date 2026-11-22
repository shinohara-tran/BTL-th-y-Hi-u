"""Gom ứng viên để gán nhãn (pooling).

Chạy mọi cách tìm cho từng câu hỏi, lấy top-N của mỗi cách, gộp lại thành một
danh sách chunk cần người đọc và chấm 0/1/2. Nhãn đã có trong file cũ được giữ
nguyên: chạy lại sau khi có cấu hình mới chỉ thêm các chunk chưa ai chấm.

    python scripts/team/pool.py
    python scripts/team/pool.py --depth 20 --methods bm25 dense rerank
"""

from __future__ import annotations

import argparse
from typing import Dict, List, Sequence

import common


def pool(engine, queries: Sequence[dict], depth: int, methods: Sequence[str],
         existing: List[dict]) -> List[dict]:
    rows = list(existing)
    index: Dict[tuple, dict] = {(r["qid"], r["chunk_id"]): r for r in rows}
    for q in queries:
        for method in methods:
            for rank, hit in enumerate(engine.search(query=q["query"], method=method, k=depth), start=1):
                key = (q["id"], hit.chunk_id)
                row = index.get(key)
                if row is None:
                    row = {
                        "qid": q["id"], "category": q["category"], "query": q["query"],
                        "chunk_id": hit.chunk_id, "ticker": hit.ticker, "form": hit.document_type,
                        "period": hit.fiscal_period, "section": hit.section,
                        "found_by": "", "best_rank": rank,
                        "label_A": "", "label_B": "", "label": "", "note": "",
                        "text": " ".join((hit.text or "").split()),
                    }
                    rows.append(row)
                    index[key] = row
                found = set(filter(None, str(row.get("found_by", "")).split("|")))
                found.add(method)
                row["found_by"] = "|".join(sorted(found))
                row["best_rank"] = min(int(row.get("best_rank") or rank), rank)
    rows.sort(key=lambda r: (r["qid"], int(r["best_rank"]), r["chunk_id"]))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--queries", default=str(common.DEFAULT_QUERIES))
    ap.add_argument("--labels", default=str(common.DEFAULT_LABELS), help="File CSV để gán nhãn (được cập nhật, không ghi đè nhãn cũ)")
    ap.add_argument("--depth", type=int, default=20, help="Lấy top-N của mỗi cách tìm")
    ap.add_argument("--methods", nargs="*", default=None, help="Mặc định: tất cả cách tìm của engine")
    args = ap.parse_args()

    from pathlib import Path
    queries = common.load_queries(Path(args.queries))
    engine, _ = common.build_engine()
    methods = args.methods or engine.METHOD_NAMES
    existing = common.read_label_rows(Path(args.labels))
    before = len(existing)
    rows = pool(engine, queries, args.depth, methods, existing)
    common.write_label_rows(rows, Path(args.labels))
    todo = sum(1 for r in rows if not str(r.get("label", "")).strip())
    print(f"{len(queries)} câu hỏi, {len(rows)} dòng ({len(rows) - before} dòng mới). Còn {todo} dòng chưa có nhãn cuối.")
    print(f"Mở file để chấm: {args.labels}")


if __name__ == "__main__":
    main()
