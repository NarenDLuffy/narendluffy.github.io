"""Per-meeting health record: what the pipeline last managed to do, and what it could not.

    public/data/meetings/<slug>/health.json

Both refresh jobs (schedule ingestion and the drafts scan) call `record()` at the
end of their run, each replacing only its own section. The record therefore
always reflects the last real attempt, including a run that published nothing.

Why this exists: every optional source fails silently by design — a missing
remote-server address, an unreachable mirror, a schedule still built from a
Draft. The site keeps serving the last good data, which is correct, but a
skipped source then looks exactly like a healthy run. The warnings computed here
are what makes that difference visible on the Ingestion status page and in the
daily verify job.

The file is rewritten only when its meaningful content changes: `updatedAt`
alone must not cause a commit every few minutes.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

MEETINGS_DIR = Path("public/data") / "meetings"
HEALTH_FILE = "health.json"
SCHEMA_VERSION = 1

# During a meeting week the refresh jobs run every few minutes; anything older
# than this means the meeting is being served stale data.
STALE_HOURS = 6


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def path_for(slug: str) -> Path:
    return MEETINGS_DIR / slug / HEALTH_FILE


def load(slug: str) -> dict[str, Any]:
    path = path_for(slug)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def save(slug: str, record: dict[str, Any]) -> None:
    path = path_for(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2))


def _without_stamp(record: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in record.items() if k != "updatedAt"}


def _meeting_meta(slug: str) -> dict[str, Any]:
    path = MEETINGS_DIR / slug / "meeting.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _hours_since(iso: str | None, now: datetime) -> float | None:
    if not iso:
        return None
    try:
        then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (now - then).total_seconds() / 3600


def _warn(level: str, text: str) -> dict[str, str]:
    return {"level": level, "text": text}


def _warnings(record: dict[str, Any], meeting: dict[str, Any], now: datetime) -> list[dict]:
    """Plain-language problems, most important first."""
    out: list[dict] = []
    status = meeting.get("status") or "unknown"
    active = status == "active"
    sched = record.get("schedule") or {}
    drafts = record.get("drafts") or {}
    remote = record.get("remoteFtp") or {}
    state = remote.get("state")

    # --- timetable ---
    if not sched.get("sessionCount"):
        out.append(
            _warn(
                "warn" if active else "info",
                "No timetable has been published for this meeting yet.",
            )
        )
    else:
        age = _hours_since(sched.get("lastSuccessAt"), now)
        if active and age is not None and age > STALE_HOURS:
            out.append(
                _warn(
                    "warn",
                    f"Timetable last rebuilt {int(age)} h ago — the refresh is not keeping up.",
                )
            )
        if sched.get("draftOnly") and active:
            out.append(
                _warn(
                    "warn",
                    "The timetable is still built from a Draft schedule; the official one has "
                    "not been picked up.",
                )
            )
        if sched.get("lowConfidenceCount"):
            out.append(
                _warn(
                    "info",
                    f"{sched['lowConfidenceCount']} document(s) parsed with low confidence.",
                )
            )
        if sched.get("conflictCount"):
            out.append(
                _warn("info", f"{sched['conflictCount']} unresolved source conflict(s).")
            )

    # --- drafts ---
    if not drafts.get("artifactCount"):
        out.append(
            _warn(
                "warn" if active else "info",
                "No draft index has been published for this meeting yet.",
            )
        )
    else:
        age = _hours_since(drafts.get("lastSuccessAt"), now)
        if active and age is not None and age > STALE_HOURS:
            out.append(
                _warn(
                    "warn",
                    f"Drafts last scanned {int(age)} h ago — the refresh is not keeping up.",
                )
            )
        if drafts.get("hiddenCount"):
            out.append(
                _warn(
                    "info",
                    f"{drafts['hiddenCount']} file(s) the meeting server no longer holds are "
                    "hidden.",
                )
            )
        read, total = drafts.get("readFolderCount"), drafts.get("folderCount")
        if active and read is not None and total and read < total:
            out.append(
                _warn("info", f"Only {read} of {total} draft folders were opened this scan.")
            )

    # --- remote meeting server ---
    if state == "skipped-no-credentials":
        out.append(
            _warn(
                "warn",
                "Remote meeting FTP login is not saved in GitHub (MEETING_FTP_USER / "
                "MEETING_FTP_PASS), so the venue copy is never read.",
            )
        )
    elif state == "skipped-no-host":
        out.append(
            _warn(
                "warn",
                "No remote meeting server address is known for this meeting, so the venue copy "
                "is not read. Enter it on the Drafts page.",
            )
        )
    elif state == "unreachable":
        out.append(
            _warn(
                "warn",
                f"Remote meeting server {remote.get('host')} was entered but did not answer.",
            )
        )
    elif state in ("read", "detected"):
        out.append(
            _warn("info", f"Remote meeting server {remote.get('host')} is being read.")
        )

    return out


def record(
    slug: str,
    *,
    schedule: dict[str, Any] | None = None,
    drafts: dict[str, Any] | None = None,
    remote: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Merge this run's sections into the meeting's health record.

    Returns the record that is now on disk (or in memory when nothing changed).
    """
    stamp = now or datetime.now(timezone.utc)
    existing = load(slug)
    meeting = _meeting_meta(slug)

    updated = dict(existing)
    updated["schemaVersion"] = SCHEMA_VERSION
    updated["meetingId"] = meeting.get("id") or existing.get("meetingId") or slug
    for section, payload in (("schedule", schedule), ("drafts", drafts), ("remoteFtp", remote)):
        if payload is not None:
            updated[section] = payload

    updated["warnings"] = _warnings(updated, meeting, stamp)

    if _without_stamp(updated) == _without_stamp(existing):
        return existing  # nothing moved: keep the file (and the commit) untouched

    updated["updatedAt"] = _now()
    save(slug, updated)
    return updated


# --- detected remote-server address (see ingestion/remote_ftp.py) ---


def cached_detected_host(slug: str) -> str | None:
    host = load(slug).get("detectedHost")
    return host if isinstance(host, str) and host else None


def remember_detected_host(slug: str, host: str) -> None:
    record = load(slug)
    if record.get("detectedHost") == host:
        return
    record["detectedHost"] = host
    record.setdefault("meetingId", slug)
    record["schemaVersion"] = SCHEMA_VERSION
    record["updatedAt"] = _now()
    save(slug, record)


def schedule_section(bundle: Any) -> dict[str, Any]:
    """Summarise a ScheduleBundle for the health record (never its contents)."""
    ingest = getattr(bundle, "ingest", None)
    sessions = list(getattr(bundle, "sessions", []) or [])
    sources = list(getattr(bundle, "sources", []) or [])
    schedule_sources = [s for s in sources if getattr(s, "type", "") != "unknown_schedule"]
    draft_only = bool(schedule_sources) and all(
        "draft" in (getattr(s, "fileName", "") or "").lower().split("ran1")[0]
        for s in schedule_sources
    )
    return {
        "state": getattr(ingest, "state", "ok"),
        "lastSuccessAt": getattr(ingest, "lastSuccessfulAt", None),
        "lastAttemptAt": getattr(ingest, "lastAttemptAt", None),
        "sessionCount": len(sessions),
        "roomCount": len(list(getattr(bundle, "rooms", []) or [])),
        "dates": sorted({s.date for s in sessions}),
        "sourceCount": len(schedule_sources),
        "sources": [
            {
                "label": getattr(s, "label", ""),
                "fileName": getattr(s, "fileName", ""),
                "origin": getattr(s, "origin", ""),
            }
            for s in schedule_sources
        ],
        "draftOnly": draft_only,
        "conflictCount": len(list(getattr(bundle, "conflicts", []) or [])),
        "lowConfidenceCount": sum(
            1 for s in sources if (getattr(s, "confidence", 1) or 1) < 0.8
        ),
    }


def drafts_section(index_json: dict[str, Any], *, source_label: str) -> dict[str, Any]:
    """Summarise a drafts index for the health record."""
    artifacts = list(index_json.get("artifacts") or [])
    folders = list(index_json.get("folders") or [])
    stamp = index_json.get("lastSuccessfulScanAt")
    return {
        "state": index_json.get("scanState"),
        "lastSuccessAt": stamp,
        "source": source_label,
        "artifactCount": len([a for a in artifacts if not a.get("removedAt")]),
        "hiddenCount": len([a for a in artifacts if a.get("removedAt")]),
        "folderCount": len(folders),
        "readFolderCount": len([f for f in folders if f.get("lastSeenAt") == stamp]),
        "eventCount": len(list(index_json.get("events") or [])),
    }


def stale_hours(record: dict[str, Any], section: str, now: datetime) -> float | None:
    """Age of a section's last success, for the verify job's freshness assertion."""
    return _hours_since((record.get(section) or {}).get("lastSuccessAt"), now)


def is_stale(record: dict[str, Any], section: str, now: datetime) -> bool:
    age = stale_hours(record, section, now)
    return age is not None and age > timedelta(hours=STALE_HOURS).total_seconds() / 3600
