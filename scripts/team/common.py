"""Shared helpers for the team evaluation scripts (queries, label files, engine)."""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path
from typing import Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUERIES = ROOT / "evaluation" / "team" / "queries.yaml"
DEFAULT_LABELS = ROOT / "evaluation" / "team" / "labels.csv"
DEFAULT_RESULTS = ROOT / "evaluation" / "team" / "results"

LABEL_COLUMNS = [
    "qid", "category", "query", "chunk_id", "ticker", "form", "period", "section",
    "found_by", "best_rank", "label_A", "label_B", "label", "note", "text",
]
VALID_GRADES = {"0", "1", "2"}


def load_queries(path: Path = DEFAULT_QUERIES, split: str = "all") -> List[dict]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    queries = data.get("queries", [])
    seen = set()
    for q in queries:
        for key in ("id", "query", "category"):
            if not q.get(key):
                raise ValueError(f"Query is missing '{key}': {q}")
        if q["id"] in seen:
            raise ValueError(f"Duplicate query id: {q['id']}")
        seen.add(q["id"])
        q.setdefault("expected_tickers", [])
        q.setdefault("split", "test")
    if split != "all":
        queries = [q for q in queries if q["split"] == split]
    return queries


def read_label_rows(path: Path = DEFAULT_LABELS) -> List[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_label_rows(rows: List[dict], path: Path = DEFAULT_LABELS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    # utf-8-sig so Excel opens Vietnamese text correctly
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LABEL_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in LABEL_COLUMNS})
    tmp.replace(path)  # write-then-rename so a crash never leaves a half-written label file


def load_qrels(path: Path = DEFAULT_LABELS) -> Dict[str, Dict[str, int]]:
    """{qid: {chunk_id: grade}} from the final 'label' column. Blank labels are skipped."""
    qrels: Dict[str, Dict[str, int]] = {}
    for r in read_label_rows(path):
        g = (r.get("label") or "").strip()
        if g == "":
            continue
        if g not in VALID_GRADES:
            raise ValueError(f"Invalid label '{g}' for {r.get('qid')}/{r.get('chunk_id')}: use 0, 1 or 2")
        qrels.setdefault(r["qid"], {})[r["chunk_id"]] = int(g)
    return qrels


def git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, timeout=10)
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True, timeout=10)
        sha = out.stdout.strip() or "unknown"
        return sha + ("-dirty" if dirty.stdout.strip() else "")
    except Exception:
        return "unknown"


def build_engine():
    from hybrid_search.config import load_config
    from hybrid_search.retrieval.engine import SearchEngine
    config = load_config()
    return SearchEngine(config=config), config
