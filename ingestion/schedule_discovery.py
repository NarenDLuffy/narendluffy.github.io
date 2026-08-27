"""Find every schedule-bearing document anywhere under a meeting folder.

Two independent problems are solved here:

  1. *Where* documents live. A schedule can sit directly in Inbox/, in
     Inbox/drafts/, in a sub-chair's personal folder, or several levels deeper
     inside a topic working folder. The tree is therefore walked recursively,
     with no folder name, chair name or meeting number hard coded.

  2. *Whether* a document is a schedule. File names are unreliable ("Chair
     notes v07.docx" is a schedule, "schedule of the social event.docx" is
     not), so the document text itself is scored: weekday names, time ranges,
     agenda codes, room/session vocabulary. The file name only adds evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote

from docx import Document

from .portal import list_folder

DOC_EXTENSIONS = (".doc", ".docx", ".xls", ".xlsx", ".pdf", ".zip", ".csv")
DEFAULT_SUBFOLDERS = ("Agenda", "Inbox", "Invitation")
MAX_DEPTH = 4

# Folders that never hold a schedule and are expensive to walk.
SKIP_FOLDER_RE = re.compile(r"^(zip|pdf|word|_+|archive|old)$", re.I)


@dataclass(frozen=True)
class FoundFile:
    url: str
    name: str
    depth: int

    @property
    def folder(self) -> str:
        return self.url.rsplit("/", 1)[0] + "/"


def walk_documents(
    folder_url: str,
    subfolders: tuple[str, ...] = DEFAULT_SUBFOLDERS,
    max_depth: int = MAX_DEPTH,
) -> list[FoundFile]:
    """Every candidate document under the given meeting folder, recursively."""
    found: list[FoundFile] = []
    seen: set[str] = set()

    def walk(url: str, depth: int) -> None:
        if depth > max_depth or url in seen:
            return
        seen.add(url)
        for entry in list_folder(url):
            name = unquote(entry.rstrip("/").rsplit("/", 1)[-1])
            if name.lower().endswith(DOC_EXTENSIONS):
                found.append(FoundFile(url=entry, name=name, depth=depth))
            elif not SKIP_FOLDER_RE.match(name):
                walk(entry.rstrip("/") + "/", depth + 1)

    for sub in subfolders:
        walk(f"{folder_url}{sub}/", 1)
    return found


# --- content classification --------------------------------------------------

WEEKDAY_RE = re.compile(r"\b(mon|tues|wednes|thurs|fri)day\b", re.I)
TIME_RANGE_RE = re.compile(r"\b\d{1,2}[:.]\d{2}\s*(?:~|-|–|—|to)\s*\d{1,2}[:.]\d{2}")
AGENDA_CODE_RE = re.compile(r"\b\d{1,2}(?:\.\d{1,2}){1,3}\b")
BREAK_RE = re.compile(r"\b(coffee|lunch|dinner)\b", re.I)
ROOM_RE = re.compile(r"\b(room|brk|breakout|plenary|hall|main session)\b", re.I)
SCHEDULE_WORD_RE = re.compile(
    r"\b(schedules?|session plans?|online sessions?|offline sessions?|agenda)\b", re.I
)
NAME_HINT_RE = re.compile(r"\b(schedules?|sessions?|agenda|plans?|notes)\b", re.I)
STRONG_NAME_RE = re.compile(r"\b(schedules?|session plans?|timetables?)\b", re.I)
CHAIR_NAME_RE = re.compile(r"\b(chair|notes|agenda)\b", re.I)
# Discussion documents: never a schedule, and there are hundreds of them.
DISCUSSION_NAME_RE = re.compile(
    r"\b(summary|moderator|fl[\s_-]|way\s*forward|\bwf\b|\bcr\b|\bls\b|reply|"
    r"proposal|contribution|feature\s*lead|email\s*discussion)\b",
    re.I,
)


def name_priority(file_name: str) -> int:
    """How likely the name alone makes this a schedule (content still decides)."""
    if DISCUSSION_NAME_RE.search(file_name) and not STRONG_NAME_RE.search(file_name):
        return -1
    if STRONG_NAME_RE.search(file_name):
        return 3
    if CHAIR_NAME_RE.search(file_name):
        return 2
    if NAME_HINT_RE.search(file_name):
        return 1
    return 0

# Content role, derived from the document's own words - never from a person.
ROLE_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("detailed", ("detailed schedule", "detail schedule", "session plan")),
    ("online", ("online session", "online schedule")),
    ("offline", ("offline session", "offline schedule", "offline discussion")),
    ("subchair", ("sub-chair", "subchair", "vice chair", "vice-chair")),
    ("main", ("online and offline", "agenda and schedule", "main session", "week schedule")),
]


@dataclass
class ContentVerdict:
    is_schedule: bool
    score: int
    role: str
    signals: dict[str, int]


def docx_text(path: str, limit: int = 60000) -> str:
    """All readable text of a DOCX: paragraphs, tables and floating boxes."""
    document = Document(path)
    chunks: list[str] = []
    for element in document.element.body.iter():
        if element.tag.endswith("}t") and element.text:
            chunks.append(element.text)
            if sum(len(c) for c in chunks) > limit:
                break
    return "\n".join(chunks)


def classify_content(text: str, file_name: str = "") -> ContentVerdict:
    """Deterministic score first; the file name is only supporting evidence."""
    signals = {
        "weekdays": len(set(m.group(0).lower() for m in WEEKDAY_RE.finditer(text))),
        "timeRanges": len(TIME_RANGE_RE.findall(text)),
        "agendaCodes": len(set(AGENDA_CODE_RE.findall(text))),
        "breaks": 1 if BREAK_RE.search(text) else 0,
        "rooms": 1 if ROOM_RE.search(text) else 0,
        "scheduleWords": 1 if SCHEDULE_WORD_RE.search(text) else 0,
    }
    score = (
        min(signals["weekdays"], 5) * 3
        + min(signals["timeRanges"], 10) * 2
        + min(signals["agendaCodes"], 10)
        + signals["breaks"] * 2
        + signals["rooms"] * 2
        + signals["scheduleWords"] * 3
    )
    if NAME_HINT_RE.search(file_name):
        score += 3

    lowered = f"{file_name}\n{text[:4000]}".lower()
    role = "unknown"
    for candidate, keywords in ROLE_RULES:
        if any(k in lowered for k in keywords):
            role = candidate
            break

    # A real week schedule always has several weekdays AND several time ranges.
    is_schedule = (
        signals["weekdays"] >= 2 and signals["timeRanges"] >= 3 and signals["agendaCodes"] >= 1
    ) or (signals["timeRanges"] >= 6 and signals["agendaCodes"] >= 3)
    return ContentVerdict(is_schedule=is_schedule, score=score, role=role, signals=signals)


def inspect_docx(path: str, file_name: str = "") -> ContentVerdict:
    try:
        return classify_content(docx_text(path), file_name)
    except Exception:
        return ContentVerdict(False, 0, "unknown", {})
