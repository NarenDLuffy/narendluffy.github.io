"""Audit: where did a chair schedule say more than the published timetable?

    python -m ingestion.audit_granularity --meeting 126-bis

Rebuilds nothing. Reads the health record the last rebuild wrote and prints
every finer breakdown, gap and table-cell problem, each sorted into a known
cause so the matching fix pattern (see the schedule-granularity-audit skill)
can be applied. Exit code 1 when anything is listed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CAUSES = [
    ("range-minutes", re.compile(r"\(\s*\d+\s*[-–~]\s*\d+\s*\)")),
    ("wildcard-x", re.compile(r"\.x\b", re.I)),
    ("bare-codes", re.compile(r"(?:^|[;:]\s|\d\s)(\d{1,2})\s+[A-Za-z]")),
    ("untimed-topic", re.compile(r"\d{2}:\d{2} [A-Za-z][^;0-9]*(?:;|$)")),
]


def classify(text: str) -> str:
    for name, pattern in CAUSES:
        if pattern.search(text):
            return name
    if "no session" in text:
        return "gap (continuation row / dropped cell)"
    if "table cell was read into" in text or "in both" in text:
        return "cell read twice / wrong colour"
    return "grid copy beat the chair table (check ranking, typo minutes)"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--meeting", required=True, help="slug fragment, e.g. 126-bis")
    args = parser.parse_args()
    base = Path("public/data/meetings")
    slugs = [p for p in base.iterdir() if p.is_dir() and p.name.endswith(args.meeting)]
    if not slugs:
        print(f"no meeting matches {args.meeting}")
        return 2
    record = json.loads((slugs[0] / "health.json").read_text())
    sched = record.get("schedule") or {}
    found = [*(sched.get("coarser") or []), *(sched.get("gaps") or []), *(sched.get("errors") or [])]
    print(f"{slugs[0].name}: state={sched.get('state')} sources={[s['fileName'] for s in sched.get('sources', [])]}")
    for item in found:
        print(f"  [{classify(item)}] {item}")
    print("no mismatches" if not found else f"{len(found)} mismatch(es)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
