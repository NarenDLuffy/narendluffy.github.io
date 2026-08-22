"""Build publishable meeting bundles from live 3GPP data.

Sources, in order of authority:

  1. the 3GPP portal meeting service (dates, city, country, timezone, folder)
  2. the meeting's own 3GPP folder (agenda.csv, schedule documents)

Sessions are only published once a schedule document has actually been parsed;
until then the meeting is published with `schedulePublished = false` and the app
shows "schedule not published yet" instead of invented rooms and slots.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from datetime import datetime, timezone
from urllib.parse import unquote

from .docx_schedule import parse_schedule_docx
from .meeting_discovery import classify_document, compute_status, revision_parts
from .models import (
    AgendaItem,
    IngestStatus,
    Meeting,
    MeetingSourceFolders,
    ScheduleBundle,
    Room,
    ScheduleSource,
    Session,
)
from .portal import (
    PortalMeeting,
    _session as http,
    fetch_agenda_csv,
    fetch_meetings,
    list_folder,
)


def download_to_temp(url: str) -> str | None:
    """Fetch a document into a temp file; None when it cannot be retrieved."""
    try:
        response = http.get(url, timeout=60)
        response.raise_for_status()
    except Exception:
        return None
    suffix = os.path.splitext(unquote(url))[1][:8] or ".bin"
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as handle:
        handle.write(response.content)
    return path

DOC_SUBFOLDERS = ("Agenda", "Inbox", "Invitation")
DOC_EXTENSIONS = (".doc", ".docx", ".xls", ".xlsx", ".pdf", ".zip", ".csv")


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _topic_key(text: str) -> str:
    return hashlib.sha1(text.lower().encode()).hexdigest()[:8]


def _parent_code(code: str) -> str | None:
    return code.rsplit(".", 1)[0] if "." in code else None


def build_bundle(pm: PortalMeeting, *, with_documents: bool = True) -> ScheduleBundle:
    now = datetime.now(timezone.utc)
    meeting = Meeting(
        id=pm.slug,
        slug=pm.slug,
        name=pm.name,
        type=pm.type,  # type: ignore[arg-type]
        startDate=pm.start_date,
        endDate=pm.end_date,
        timezone=pm.timezone,
        status=compute_status(pm.start_date, pm.end_date),  # type: ignore[arg-type]
        meetingNumber=pm.number,
        city=pm.city,
        country=pm.country,
        schedulePublished=False,
        sources=MeetingSourceFolders(
            meetingFolder=pm.folder_url,
            inbox=f"{pm.folder_url}Inbox/" if pm.folder_url else None,
            agenda=f"{pm.folder_url}Agenda/" if pm.folder_url else None,
        ),
        lastIngestedAt=_iso(now),
    )

    agenda_items: list[AgendaItem] = []
    sources: list[ScheduleSource] = []
    rooms: list[Room] = []
    sessions: list[Session] = []

    if with_documents and pm.folder_url:
        for code, title in fetch_agenda_csv(pm.folder_url):
            agenda_items.append(
                AgendaItem(
                    code=code,
                    meetingId=meeting.id,
                    title=title,
                    parent=_parent_code(code),
                    topicKey=_topic_key(title),
                )
            )
        sources = discover_sources(meeting, pm.folder_url, _iso(now))
        rooms, sessions = parse_schedule_sources(meeting, sources)
        meeting.schedulePublished = bool(sessions)

    return ScheduleBundle(
        generatedAt=_iso(now),
        meeting=meeting,
        rooms=rooms,
        sessions=sessions,
        agendaItems=agenda_items,
        sources=sources,
        changes=[],
        conflicts=[],
        ingest=IngestStatus(
            state="ok",
            lastSuccessfulAt=_iso(now),
            lastAttemptAt=_iso(now),
            message=None
            if sessions
            else "No session schedule document published by 3GPP yet.",
        ),
    )


def discover_sources(meeting: Meeting, folder_url: str, retrieved_at: str) -> list[ScheduleSource]:
    """Every candidate document in the meeting folder, classified generically.

    Chairs publish their session plans in personal subfolders of Inbox (one per
    vice-chair), so folders are walked one level deep instead of assuming any
    particular folder name.
    """
    found: list[ScheduleSource] = []
    for sub in DOC_SUBFOLDERS:
        for url in list_folder(f"{folder_url}{sub}/"):
            name = unquote(url.rstrip("/").rsplit("/", 1)[-1])
            if name.lower().endswith(DOC_EXTENSIONS):
                found.append(_to_source(meeting, url, name, retrieved_at))
                continue
            # A subfolder (personal chair folder, drafts, ...): look inside once.
            for inner in list_folder(url + "/"):
                inner_name = unquote(inner.rstrip("/").rsplit("/", 1)[-1])
                if inner_name.lower().endswith(DOC_EXTENSIONS):
                    found.append(_to_source(meeting, inner, inner_name, retrieved_at))
    return _latest_revisions(found)


def _to_source(meeting: Meeting, url: str, name: str, retrieved_at: str) -> ScheduleSource:
    return ScheduleSource(
        sourceId=f"{meeting.id}-{hashlib.sha1(url.encode()).hexdigest()[:8]}",
        meetingId=meeting.id,
        fileName=name,
        label=name.rsplit(".", 1)[0][:60],
        type=classify_document(name),  # type: ignore[arg-type]
        origin="public",
        retrievedAt=retrieved_at,
        revisionParts=revision_parts(name),
        url=url,
        contentHash=hashlib.sha256(url.encode()).hexdigest(),
    )


REVISION_SUFFIX_RE = re.compile(r"[_\s-]*v?\d+(?:[._]\d+)*\s*$", re.I)


def _revision_family(source: ScheduleSource) -> str:
    stem = source.fileName.rsplit(".", 1)[0]
    return REVISION_SUFFIX_RE.sub("", stem).strip().lower()


def _latest_revisions(sources: list[ScheduleSource]) -> list[ScheduleSource]:
    """Keep only the newest revision of each document family (…_v06 < …_v07)."""
    best: dict[str, ScheduleSource] = {}
    for source in sources:
        key = f"{source.url.rsplit('/', 1)[0] if source.url else ''}|{_revision_family(source)}"
        current = best.get(key)
        if current is None or (source.revisionParts or []) > (current.revisionParts or []):
            best[key] = source
    return sorted(best.values(), key=lambda s: s.fileName.lower())


def parse_schedule_sources(
    meeting: Meeting, sources: list[ScheduleSource]
) -> tuple[list[Room], list[Session]]:
    """Download every schedule-looking DOCX and merge what it contains."""
    rooms: dict[str, Room] = {}
    sessions: list[Session] = []
    for source in sources:
        if not source.url or not source.fileName.lower().endswith(".docx"):
            continue
        if "schedule" not in source.fileName.lower() and source.type == "unknown_schedule":
            continue
        path = download_to_temp(source.url)
        if not path:
            continue
        try:
            doc_rooms, doc_sessions = parse_schedule_docx(
                path,
                meeting_id=meeting.id,
                start_date=meeting.startDate,
                end_date=meeting.endDate,
                source=source,
                room_order_offset=len(rooms),
            )
        except Exception as exc:  # a malformed document must not break the run
            print(f"  could not parse {source.fileName}: {exc}")
            continue
        for room in doc_rooms:
            rooms.setdefault(room.roomId, room)
        sessions.extend(doc_sessions)
    return list(rooms.values()), sessions


def build_live_bundles(
    *, start: str = "2025-01-01", end: str = "2028-12-31", with_documents: bool = True
) -> list[ScheduleBundle]:
    return [build_bundle(pm, with_documents=with_documents) for pm in fetch_meetings(start, end)]
