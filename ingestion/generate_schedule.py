"""Entry point run by GitHub Actions.

    python -m ingestion.generate_schedule [--force]

Pipeline:
  discover sources -> download changed docs -> parse tables -> merge
  -> detect conflicts -> validate -> diff against previous -> write JSON

Outputs (committed and deployed with the static site):
  public/schedule/schedule.json
  public/schedule/changes.json
  public/schedule/sources.json

On validation failure the previous files are left untouched, so the site keeps
serving the last verified schedule.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .change_detector import detect_changes
from .validator import validate

OUT_DIR = Path("public/schedule")
STATE_PATH = Path(".ingestion-state/sources.json")


def read_previous() -> dict | None:
    path = OUT_DIR / "schedule.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return None
    return None


def write_outputs(bundle_json: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "schedule.json").write_text(json.dumps(bundle_json, indent=2))
    (OUT_DIR / "changes.json").write_text(json.dumps(bundle_json["changes"], indent=2))
    (OUT_DIR / "sources.json").write_text(json.dumps(bundle_json["sources"], indent=2))


def build_bundle(force: bool):
    """Wire downloader -> parser -> merger here.

    Phase 2 fills this in against the live 3GPP file server. It must return a
    ScheduleBundle or None when nothing changed (so the workflow can skip the
    commit and deploy entirely).
    """
    raise NotImplementedError("Phase 2: connect downloader/parser/merger")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="ignore hashes, full rebuild")
    args = ap.parse_args()

    previous = read_previous()

    try:
        bundle = build_bundle(args.force)
    except NotImplementedError as exc:
        print(f"ingestion not yet connected: {exc}", file=sys.stderr)
        return 0  # keep the last good schedule; never publish an empty one

    if bundle is None:
        print("no source changes; nothing to publish")
        return 0

    errors = validate(bundle, previous)
    if errors:
        print("validation failed, keeping previous schedule:", *errors, sep="\n  ", file=sys.stderr)
        return 1

    bundle.changes = detect_changes(previous, bundle) + bundle.changes
    write_outputs(bundle.to_json())
    print(f"published {len(bundle.sessions)} sessions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
