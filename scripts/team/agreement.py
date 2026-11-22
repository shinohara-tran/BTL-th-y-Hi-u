"""So nhãn của 2 người chấm, tính Cohen's kappa và điền nhãn cuối.

Mỗi dòng trong labels.csv có label_A (người 1) và label_B (người 2), chấm độc lập.
Script này:
  - tính kappa trên các dòng cả hai đã chấm,
  - điền cột 'label' khi hai người giống nhau (không đụng tới nhãn cuối đã có),
  - in ra các dòng lệch để cả nhóm thảo luận rồi tự điền 'label'.

    python scripts/team/agreement.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import common
from hybrid_search.evaluation.team_metrics import cohen_kappa


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", default=str(common.DEFAULT_LABELS))
    args = ap.parse_args()
    path = Path(args.labels)
    rows = common.read_label_rows(path)

    both, conflicts, filled = [], [], 0
    for r in rows:
        a, b = str(r.get("label_A", "")).strip(), str(r.get("label_B", "")).strip()
        for v, who in ((a, "label_A"), (b, "label_B")):
            if v and v not in common.VALID_GRADES:
                raise SystemExit(f"Nhãn không hợp lệ '{v}' ở cột {who}, dòng {r['qid']}/{r['chunk_id']}. Chỉ dùng 0, 1, 2.")
        if a and b:
            both.append((int(a), int(b)))
            if a == b and not str(r.get("label", "")).strip():
                r["label"] = a
                filled += 1
            elif a != b and not str(r.get("label", "")).strip():
                conflicts.append(r)

    common.write_label_rows(rows, path)
    if both:
        k = cohen_kappa([x for x, _ in both], [y for _, y in both])
        print(f"{len(both)} dòng có đủ 2 người chấm. Cohen's kappa = {k:.3f}")
        print("Tham khảo: > 0,6 là đồng thuận khá; < 0,4 thì nên thống nhất lại cách chấm trước khi chấm tiếp.")
    else:
        print("Chưa có dòng nào đủ 2 người chấm.")
    print(f"Đã điền nhãn cuối cho {filled} dòng hai người chấm giống nhau.")
    if conflicts:
        print(f"{len(conflicts)} dòng lệch, cần thảo luận rồi điền cột 'label':")
        for r in conflicts:
            print(f"  {r['qid']}  {r['chunk_id']}  A={r['label_A']} B={r['label_B']}  {(r.get('query') or '')[:60]}")


if __name__ == "__main__":
    main()
