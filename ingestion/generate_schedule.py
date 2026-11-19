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
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import health, remote_ftp
from .change_detector import detect_changes
from .fixtures import fixture_meetings
from .models import ScheduleSource
from .live import build_live_bundles
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
    """Publish every RAN1 meeting the 3GPP portal knows about.

    Metadata comes from the portal meeting service; agenda items and schedule
    documents come from each meeting's own 3GPP folder. `force` is accepted for
    the workflow's benefit: the portal response is small, so a full refresh is
    always performed.
    """
    from datetime import date

    return [build_for(pm) for pm in all_portal_meetings() if rebuild_due(pm.end_date, date.today(), force)]


def all_portal_meetings():
    """Every followed working group's meetings (RAN1, RAN2); one group failing never stops the other."""
    from .groups import GROUPS
    from .portal import fetch_meetings

    found = []
    for key in GROUPS:
        try:
            found.extend(fetch_meetings("2025-01-01", "2028-12-31", key))
        except Exception as exc:  # noqa: BLE001
            print(f"{key}: portal unavailable: {exc}", file=sys.stderr)
    return found


def build_for(pm) -> ScheduleBundle:
    """RAN2 has one week grid per meeting; RAN1 merges its chair files."""
    from .groups import GROUPS

    if GROUPS[pm.group].schedule_style == "single_grid":
        from .ran2_schedule import build_bundle as build_grid

        return build_grid(pm)
    if GROUPS[pm.group].schedule_style == "chair_notes_plus_sheet":
        from .ran3_schedule import build_bundle as build_ran3

        return build_ran3(pm)
    from .live import build_bundle

    return build_bundle(pm)


def rebuild_due(end_date: str, today, force: bool = False) -> bool:
    """Automatic runs rebuild only meetings not yet over (plus the day after).

    Finished meetings keep their final published schedule: their chair files are
    gone from Meetings Sync, so rebuilding them only times out the job or is
    refused, and that used to block the live meeting's refresh.
    """
    from datetime import date, timedelta

    if force:
        return True
    try:
        return date.fromisoformat(end_date[:10]) + timedelta(days=1) >= today
    except ValueError:
        return True


def _keep_failed_documents(meeting_id: str, slug: str, errors: list[str]) -> None:
    """Copy the refused update's documents to failed-schedule/ for the run.

    The GitHub job turns them into pictures so the cause can be seen by eye;
    the pictures never decide what goes into the timetable.
    """
    import shutil

    from .live import SCHEDULE_PATHS

    out = os.path.join("failed-schedule", slug)
    os.makedirs(out, exist_ok=True)
    for name, path in SCHEDULE_PATHS.get(meeting_id, []):
        try:
            shutil.copy(path, os.path.join(out, os.path.basename(name)))
        except OSError:
            pass
    with open(os.path.join(out, "errors.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(errors) + "\n")


def revision_downgrades(before: list[dict], after: list[dict]) -> list[str]:
    """Refuse a rebuild that reads an older revision than the one already published.

    After the meeting the folders that held the final chair files (Meetings
    Sync, the venue) are gone, and the meeting folder often only has early
    revisions: rebuilding from those would replace the final schedule with a
    stale one.
    """
    from .live import _is_draft, _revision_family
    from .meeting_discovery import revision_parts

    def rank(name: str) -> tuple:
        probe = ScheduleSource(sourceId="", meetingId="", fileName=name, label="", type="chair_schedule", origin="public", retrievedAt="")
        return (not _is_draft(probe), revision_parts(name) or [])

    def families(items: list[dict]) -> dict[str, str]:
        out: dict[str, str] = {}
        for item in items:
            name = item.get("fileName") or ""
            if not name:
                continue
            probe = ScheduleSource(sourceId="", meetingId="", fileName=name, label="", type="chair_schedule", origin="public", retrievedAt="")
            key = _revision_family(probe)
            if key not in out or rank(name) > rank(out[key]):
                out[key] = name
        return out

    old, new = families(before), families(after)
    errors = []
    for key, name in old.items():
        if key not in new:
            errors.append(f"published schedule used {name}, which this rebuild no longer finds; keeping it")
        elif rank(new[key]) < rank(name):
            errors.append(f"rebuild would read {new[key]}, older than the published {name}; keeping it")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="ignore hashes, full rebuild")
    ap.add_argument(
        "--fixtures",
        action="store_true",
        help="publish the demonstration meetings instead of live documents",
    )
    ap.add_argument(
        "--meeting",
        default="",
        help="rebuild only meetings whose slug contains this text (e.g. 126-bis)",
    )
    args = ap.parse_args()

    if args.fixtures:
        bundles = fixture_meetings()
    elif args.meeting:
        wanted = args.meeting.lower()
        bundles = []
        for pm in all_portal_meetings():
            label = pm.slug
            if wanted in label.lower() or wanted in (pm.name or "").lower():
                bundles.append(build_for(pm))
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
    sections: dict[str, dict] = {}
    failed = 0
    failed_live = 0
    for bundle in bundles:
        previous = read_previous(bundle.meeting.slug)
        # During the meeting days Meetings Sync is the live source: a revision
        # the chairs removed there was withdrawn, so a rebuild without it is
        # current, not a downgrade. The guard protects the final schedule
        # once those folders are cleared after the meeting.
        from . import remote_ftp
        downgrades = revision_downgrades(
            (health.load(bundle.meeting.slug).get("schedule") or {}).get("sources") or [],
            (health.schedule_section(bundle) or {}).get("sources") or [],
        )
        if downgrades and remote_ftp.meeting_phase(bundle.meeting.startDate, bundle.meeting.endDate) == "week":
            print(f"{bundle.meeting.name}: revisions withdrawn on Meetings Sync:", *downgrades, sep="\n  ")
            downgrades = []
        errors = validate(bundle, previous) + downgrades
        if errors:
            failed += 1
            if compute_status(bundle.meeting.startDate, bundle.meeting.endDate) != "completed":
                failed_live += 1
            print(
                f"validation failed for {bundle.meeting.name}, keeping previous schedule:",
                *errors,
                sep="\n  ",
                file=sys.stderr,
            )
            _keep_failed_documents(bundle.meeting.id, bundle.meeting.slug, errors)
            # The old schedule is still what people see: say so, don't go quiet.
            sections[bundle.meeting.slug] = {
                **(health.load(bundle.meeting.slug).get("schedule") or {}),
                "state": "validation-failed",
                "lastAttemptAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                "gaps": [e for e in errors if "no session" in e],
                "errors": errors[:20],
            }
            continue
        bundle.changes = detect_changes(previous, bundle) + bundle.changes
        write_meeting(bundle)
        published.append(bundle)
        sections[bundle.meeting.slug] = health.schedule_section(bundle)

    write_index(bundles)

    # Health record: what this run actually achieved, per meeting. Written last so
    # it always describes the last real attempt, published or not (see health.py).
    for bundle in bundles:
        section = sections.get(bundle.meeting.slug)
        if section is not None:
            health.record(
                bundle.meeting.slug,
                schedule=section,
                remote=remote_ftp.snapshot(bundle.meeting.id),
            )

    current = select_current([b.meeting for b in bundles])
    print(
        f"published {len(published)} meeting(s); "
        f"current meeting: {current.name if current else 'none'}"
    )
    # Fail only when a meeting that is running or coming up was refused.
    return 1 if failed_live else 0


if __name__ == "__main__":
    raise SystemExit(main())
