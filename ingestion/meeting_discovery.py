"""Generic discovery of RAN1 meetings and of their schedule documents.

Two hard rules, both required for the app to keep working for meetings that do
not exist yet:

  * No meeting, chair, sub-chair, room or topic name is ever hard coded. A
    meeting is whatever folder the 3GPP server exposes; a document role is
    derived from generic vocabulary in the file name.
  * Everything is keyed by a stable meeting id derived from the folder, so a
    meeting keeps its identity across renames of its display name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone

from .models import Meeting, MeetingSourceFolders

RAN1_ROOT = "https://www.3gpp.org/ftp/tsg_ran/WG1_RL1"

FOLDER_RE = re.compile(r"TSGR1_(?P<number>\d+)(?P<suffix>[A-Za-z0-9_\-]*)", re.I)
DATE_RANGE_RE = re.compile(
    r"(?P<d1>\d{1,2})\s*[-–]\s*(?P<d2>\d{1,2})\s*(?P<month>[A-Za-z]{3,})\s*(?P<year>\d{4})"
)
REVISION_RE = re.compile(r"v(?P<rev>\d+(?:[._]\d+)*)", re.I)

# Generic vocabulary only — never a person's name.
TYPE_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("venue_information", ("venue", "floorplan", "floor plan", "hotel", "logistic")),
    ("online_schedule", ("online session", "online schedule", "e-meeting")),
    ("offline_schedule", ("offline session", "offline schedule", "offline discussion")),
    ("room_schedule", ("room allocation", "room schedule", "breakout")),
    ("detailed_schedule", ("detailed schedule", "detail schedule", "session plan")),
    ("subchair_schedule", ("sub-chair", "subchair", "vice chair", "vice-chair", "session chair")),
    ("chair_schedule", ("chair notes", "chair schedule", "chairman")),
    ("main_schedule", ("agenda and schedule", "online and offline", "draft schedule", "schedule")),
]


@dataclass
class DiscoveredDocument:
    """A candidate schedule document found in a meeting folder."""

    file_name: str
    url: str
    size: int | None = None
    last_modified: str | None = None

    @property
    def type(self) -> str:
        return classify_document(self.file_name)

    @property
    def revision(self) -> str | None:
        m = REVISION_RE.search(self.file_name)
        return f"v{m.group('rev')}" if m else None

    @property
    def revision_parts(self) -> list[int]:
        return revision_parts(self.file_name)

    @property
    def label(self) -> str:
        """Human label built from the document itself, never from a person."""
        pretty = self.type.replace("_", " ").capitalize()
        return f"{pretty} {self.revision}" if self.revision else pretty


def classify_document(file_name: str) -> str:
    lowered = file_name.lower()
    for source_type, keywords in TYPE_RULES:
        if any(k in lowered for k in keywords):
            return source_type
    return "unknown_schedule"


def revision_parts(file_name: str) -> list[int]:
    m = REVISION_RE.search(file_name)
    if not m:
        return []
    return [int(p) for p in re.split(r"[._]", m.group("rev")) if p.isdigit()]


def is_schedule_document(file_name: str) -> bool:
    """Only documents that can carry a schedule are downloaded."""
    if not file_name.lower().endswith((".doc", ".docx", ".zip")):
        return False
    return classify_document(file_name) != "unknown_schedule"


def rank_documents(documents: list[DiscoveredDocument]) -> list[DiscoveredDocument]:
    """Newest revision first within each document type."""
    order = {name: i for i, (name, _) in enumerate(TYPE_RULES)}
    return sorted(
        documents,
        key=lambda d: (order.get(d.type, 99), [-p for p in d.revision_parts] or [0], d.file_name),
    )


def meeting_type(folder: str) -> str:
    lowered = folder.lower()
    if "bis" in lowered:
        return "bis"
    if "ah" in lowered.split("_") or "adhoc" in lowered or "-ah-" in lowered:
        return "adhoc"
    if FOLDER_RE.fullmatch(folder) or FOLDER_RE.match(folder):
        return "regular"
    return "other"


def parse_date_range(text: str, fallback_year: int | None = None) -> tuple[str, str] | None:
    """Parse a '18-22 Nov 2025'-style range out of any listing text."""
    m = DATE_RANGE_RE.search(text)
    if not m:
        return None
    try:
        month = datetime.strptime(m.group("month")[:3], "%b").month
    except ValueError:
        return None
    year = int(m.group("year") or fallback_year or date.today().year)
    start = date(year, month, int(m.group("d1")))
    end = date(year, month, int(m.group("d2")))
    if end < start:  # range crossing a month boundary in the listing text
        end = start
    return start.isoformat(), end.isoformat()


def meeting_from_folder(
    folder: str,
    *,
    start_date: str,
    end_date: str,
    timezone_name: str = "UTC",
    city: str | None = None,
    country: str | None = None,
    venue: str | None = None,
) -> Meeting:
    """Build a Meeting from a folder name plus whatever metadata was found."""
    m = FOLDER_RE.search(folder)
    number = int(m.group("number")) if m else None
    suffix = (m.group("suffix") or "").strip("_-") if m else ""
    kind = meeting_type(folder)
    display_suffix = f"-{suffix.lower()}" if suffix else ""
    name = f"RAN1#{number}{display_suffix}" if number else folder
    slug = f"ran1-{number}{display_suffix}" if number else folder.lower()
    return Meeting(
        id=slug,
        slug=slug,
        name=name,
        type=kind,  # type: ignore[arg-type]
        startDate=start_date,
        endDate=end_date,
        timezone=timezone_name,
        status=compute_status(start_date, end_date),
        meetingNumber=number,
        city=city,
        country=country,
        venue=venue,
        sources=MeetingSourceFolders(meetingFolder=f"{RAN1_ROOT}/{folder}/"),
    )


def compute_status(start_date: str, end_date: str, at: date | None = None) -> str:
    today = (at or datetime.now(timezone.utc).date()).isoformat()
    if today < start_date:
        return "upcoming"
    if today > end_date:
        return "completed"
    return "active"


def select_current(meetings: list[Meeting]) -> Meeting | None:
    """In progress -> nearest upcoming -> most recently completed."""
    if not meetings:
        return None
    active = [m for m in meetings if m.status == "active"]
    if active:
        return sorted(active, key=lambda m: m.startDate)[0]
    upcoming = [m for m in meetings if m.status == "upcoming"]
    if upcoming:
        return sorted(upcoming, key=lambda m: m.startDate)[0]
    return sorted(meetings, key=lambda m: m.endDate)[-1]


def parse_listing(html: str) -> list[str]:
    """Folder / file names from a 3GPP directory listing page."""
    names = re.findall(r'href="[^"]*/([^"/]+)/?"', html, re.I)
    seen: list[str] = []
    for n in names:
        if n not in seen and not n.startswith("?"):
            seen.append(n)
    return seen


def discover_meeting_folders(listing: list[str]) -> list[str]:
    folders = [n for n in listing if FOLDER_RE.match(n)]
    return sorted(
        folders,
        key=lambda n: (int(FOLDER_RE.match(n).group("number")), n),  # type: ignore[union-attr]
    )
