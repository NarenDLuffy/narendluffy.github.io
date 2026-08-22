"""Entry point for the draft-watch workflow.

    python -m draft_tracker.update_drafts [--all] [--hash]

Meetings come from the existing discovery output (`public/data/meetings.json`),
so a brand new RAN1 meeting is tracked with no code change. Polling is
adaptive: active meetings are always scanned, upcoming meetings are scanned so
their tree is baselined before the week starts, and completed meetings keep
their archived index without being polled again.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .notifier import group_events
from .public_source import Public3GPPDraftSource
from .state_store import load_previous, save_index
from .tracker import ScanConfig, scan_meeting

DATA_DIR = Path("public/data")
MEETINGS_DIR = DATA_DIR / "meetings"
UPCOMING_WINDOW_DAYS = 21


def _load_meetings() -> list[dict]:
    path = DATA_DIR / "meetings.json"
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("meetings", [])


def _agenda_codes(slug: str) -> dict[str, str]:
    path = MEETINGS_DIR / slug / "agenda.json"
    if not path.exists():
        return {}
    try:
        return {row["code"]: row.get("title", "") for row in json.loads(path.read_text())}
    except (json.JSONDecodeError, KeyError, TypeError):
        return {}


def _meeting_folder(slug: str) -> str | None:
    path = MEETINGS_DIR / slug / "meeting.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    sources = data.get("sources") or {}
    return sources.get("meetingFolder")


def should_scan(meeting: dict, scan_all: bool) -> bool:
    """Adaptive polling: never keep hammering old meetings."""
    if scan_all:
        return True
    status = meeting.get("status")
    if status == "active":
        return True
    if status == "upcoming":
        try:
            start = date.fromisoformat(meeting["startDate"])
        except (KeyError, ValueError):
            return False
        return start - date.today() <= timedelta(days=UPCOMING_WINDOW_DAYS)
    # Completed meetings: scan once more only if never baselined (archive it).
    return load_previous(meeting["slug"]) is None and _recently_completed(meeting)


def _recently_completed(meeting: dict) -> bool:
    try:
        end = date.fromisoformat(meeting["endDate"])
    except (KeyError, ValueError):
        return False
    return date.today() - end <= timedelta(days=30)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="scan every known meeting")
    ap.add_argument("--hash", action="store_true", help="download FL summaries to fingerprint")
    ap.add_argument("--slug", help="scan a single meeting slug")
    args = ap.parse_args()

    meetings = _load_meetings()
    if args.slug:
        meetings = [m for m in meetings if m.get("slug") == args.slug]

    scanned = 0
    for meeting in meetings:
        slug = meeting.get("slug")
        if not slug or not should_scan(meeting, args.all or bool(args.slug)):
            continue
        folder = _meeting_folder(slug)
        source = Public3GPPDraftSource(folder)
        previous = load_previous(slug)
        index = scan_meeting(
            meeting_id=meeting.get("id", slug),
            source=source,
            agenda_codes=_agenda_codes(slug),
            previous=previous,
            monitoring=meeting.get("status") != "completed",
            config=ScanConfig(hash_files=args.hash),
        )
        payload = index.to_json()
        fresh_ids = set(index.newEventIds)
        payload["notifications"] = group_events([e for e in index.events if e.id in fresh_ids])
        save_index(slug, payload)
        scanned += 1
        fresh = len(index.newEventIds)
        print(
            f"{slug}: {index.scanState}, {len(index.artifacts)} artifacts, "
            f"{len(index.folders)} folders, {fresh} new event(s)"
        )

    if scanned == 0:
        print("no meeting currently requires a draft scan")
    print(f"scanned {scanned} meeting(s) at {datetime.now(timezone.utc).isoformat()}Z")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
