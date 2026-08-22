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
from datetime import datetime, timezone

from .meeting_discovery import classify_document, compute_status, revision_parts
from .models import (
    AgendaItem,
    IngestStatus,
    Meeting,
    MeetingSourceFolders,
    ScheduleBundle,
    ScheduleSource,
)
from .portal import PortalMeeting, fetch_agenda_csv, fetch_meetings, list_folder

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

    return ScheduleBundle(
        generatedAt=_iso(now),
        meeting=meeting,
        rooms=[],
        sessions=[],
        agendaItems=agenda_items,
        sources=sources,
        changes=[],
        conflicts=[],
        ingest=IngestStatus(
            state="ok",
            lastSuccessfulAt=_iso(now),
            lastAttemptAt=_iso(now),
            message=None
            if agenda_items
            else "Agenda and schedule documents not published by 3GPP yet.",
        ),
    )


def discover_sources(meeting: Meeting, folder_url: str, retrieved_at: str) -> list[ScheduleSource]:
    """Every candidate document in the meeting folder, classified generically."""
    found: list[ScheduleSource] = []
    for sub in DOC_SUBFOLDERS:
        for url in list_folder(f"{folder_url}{sub}/"):
            file_name = url.rstrip("/").rsplit("/", 1)[-1]
            if not file_name.lower().endswith(DOC_EXTENSIONS):
                continue
            from urllib.parse import unquote

            pretty = unquote(file_name)
            source_type = classify_document(pretty)
            found.append(
                ScheduleSource(
                    sourceId=f"{meeting.id}-{hashlib.sha1(url.encode()).hexdigest()[:8]}",
                    meetingId=meeting.id,
                    fileName=pretty,
                    label=pretty.rsplit(".", 1)[0][:60],
                    type=source_type,  # type: ignore[arg-type]
                    origin="public",
                    retrievedAt=retrieved_at,
                    revisionParts=revision_parts(pretty),
                    url=url,
                    contentHash=hashlib.sha256(url.encode()).hexdigest(),
                )
            )
    return found


def build_live_bundles(
    *, start: str = "2025-01-01", end: str = "2028-12-31", with_documents: bool = True
) -> list[ScheduleBundle]:
    return [build_bundle(pm, with_documents=with_documents) for pm in fetch_meetings(start, end)]
