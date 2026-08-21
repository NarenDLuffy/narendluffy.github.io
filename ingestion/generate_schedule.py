"""Entry point run by GitHub Actions.

    python -m ingestion.generate_schedule [--force] [--fixtures]

Pipeline per discovered meeting:

  discover meetings -> discover + download changed documents -> parse ->
  merge with provenance -> detect conflicts -> validate -> diff against the
  previous published version -> write JSON

Outputs (committed and deployed with the static site):

  public/data/meetings.json                     meeting registry
  public/data/meetings/<slug>/meeting.json
  public/data/meetings/<slug>/schedule.json     sessions + ingest status
  public/data/meetings/<slug>/rooms.json
  public/data/meetings/<slug>/agenda.json
  public/data/meetings/<slug>/sources.json
  public/data/meetings/<slug>/changes.json

When a meeting cannot be refreshed, its previously published files are left
untouched, so the site always keeps serving the last verified schedule.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .change_detector import detect_changes
from .fixtures import fixture_meetings
from .meeting_discovery import compute_status, select_current
from .models import SCHEMA_VERSION, ScheduleBundle
from .validator import validate

OUT_DIR = Path("public/data")
MEETINGS_DIR = OUT_DIR / "meetings"
STATE_PATH = Path(".ingestion-state/sources.json")


def read_previous(slug: str) -> dict | None:
    path = MEETINGS_DIR / slug / "schedule.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return None
    return None


def write_meeting(bundle: ScheduleBundle) -> None:
    data = bundle.to_json()
    slug = bundle.meeting.slug
    out = MEETINGS_DIR / slug
    out.mkdir(parents=True, exist_ok=True)

    (out / "meeting.json").write_text(json.dumps(data["meeting"], indent=2))
    (out / "schedule.json").write_text(
        json.dumps(
            {
                "schemaVersion": data["schemaVersion"],
                "generatedAt": data["generatedAt"],
                "meetingId": bundle.meeting.id,
                "sessions": data["sessions"],
                "conflicts": data["conflicts"],
                "ingest": data["ingest"],
            },
            indent=2,
        )
    )
    (out / "rooms.json").write_text(json.dumps(data["rooms"], indent=2))
    (out / "agenda.json").write_text(json.dumps(data["agendaItems"], indent=2))
    (out / "sources.json").write_text(json.dumps(data["sources"], indent=2))
    (out / "changes.json").write_text(json.dumps(data["changes"], indent=2))


def write_index(bundles: list[ScheduleBundle]) -> None:
    """Registry of every known meeting, newest first."""
    existing: dict[str, dict] = {}
    index_path = OUT_DIR / "meetings.json"
    if index_path.exists():
        try:
            for m in json.loads(index_path.read_text()).get("meetings", []):
                existing[m["id"]] = m
        except (json.JSONDecodeError, KeyError):
            existing = {}

    for bundle in bundles:
        meeting = bundle.meeting.to_json()
        meeting["status"] = compute_status(bundle.meeting.startDate, bundle.meeting.endDate)
        meeting["schedulePublished"] = bool(bundle.sessions)
        existing[meeting["id"]] = meeting

    meetings = sorted(existing.values(), key=lambda m: m["startDate"], reverse=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(
            {
                "schemaVersion": SCHEMA_VERSION,
                "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "meetings": meetings,
            },
            indent=2,
        )
    )


def build_bundles(force: bool) -> list[ScheduleBundle]:
    """Wire meeting_discovery -> downloader -> parser -> merger here.

    Must return one ScheduleBundle per meeting that changed. Raising
    NotImplementedError keeps the previously published data in place.
    """
    raise NotImplementedError("live 3GPP ingestion not connected yet")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="ignore hashes, full rebuild")
    ap.add_argument(
        "--fixtures",
        action="store_true",
        help="publish the demonstration meetings instead of live documents",
    )
    args = ap.parse_args()

    if args.fixtures:
        bundles = fixture_meetings()
    else:
        try:
            bundles = build_bundles(args.force)
        except NotImplementedError as exc:
            print(f"ingestion not yet connected: {exc}", file=sys.stderr)
            return 0  # keep the last good schedule; never publish an empty one

    if not bundles:
        print("no source changes; nothing to publish")
        return 0

    published: list[ScheduleBundle] = []
    failed = 0
    for bundle in bundles:
        previous = read_previous(bundle.meeting.slug)
        errors = validate(bundle, previous)
        if errors:
            failed += 1
            print(
                f"validation failed for {bundle.meeting.name}, keeping previous schedule:",
                *errors,
                sep="\n  ",
                file=sys.stderr,
            )
            continue
        bundle.changes = detect_changes(previous, bundle) + bundle.changes
        write_meeting(bundle)
        published.append(bundle)

    write_index(bundles)

    current = select_current([b.meeting for b in bundles])
    print(
        f"published {len(published)} meeting(s); "
        f"current meeting: {current.name if current else 'none'}"
    )
    return 1 if failed and not published else 0


if __name__ == "__main__":
    raise SystemExit(main())
