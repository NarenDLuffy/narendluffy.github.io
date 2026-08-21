"""Deterministic DOCX table extraction (python-docx).

Deliberate rule: no LLM is used for anything a table walk can answer. An LLM
may only be called for genuinely ambiguous free-text cells, and never to
resolve a conflict between two documents.

Handles the awkward parts of the RAN1 schedule documents:
  * merged/spanned cells (repeat the parent value across the span)
  * room names in the header row
  * time ranges in the first column
  * agenda item codes anywhere in the cell text
"""

from __future__ import annotations

import re
from typing import Iterable

from .models import Session, SessionSourceRef

TIME_RE = re.compile(r"(\d{1,2})[:.](\d{2})\s*[-–—]\s*(\d{1,2})[:.](\d{2})")
AGENDA_RE = re.compile(r"\b(\d{1,2}(?:\.\d{1,2}){1,4})\b")

TOPIC_KEYWORDS = {
    "isac": ("isac", "sensing"),
    "waveform": ("waveform",),
    "aiot": ("a-iot", "aiot", "ambient"),
    "aiml": ("ai/ml", "ai / ml", "aiml", "machine learning"),
    "mimo": ("mimo", "csi", "beam"),
    "ntn": ("ntn", "satellite", "non-terrestrial"),
    "maintenance": ("maintenance", "plenary", "opening", "closing"),
}


def normalize_time(hh: str, mm: str) -> str:
    return f"{int(hh):02d}:{mm}"


def parse_time_range(text: str) -> tuple[str, str] | None:
    m = TIME_RE.search(text or "")
    if not m:
        return None
    return normalize_time(m.group(1), m.group(2)), normalize_time(m.group(3), m.group(4))


def extract_agenda_items(text: str) -> list[str]:
    return sorted({m.group(1) for m in AGENDA_RE.finditer(text or "")})


def topic_key_for(text: str) -> str:
    lowered = (text or "").lower()
    for key, words in TOPIC_KEYWORDS.items():
        if any(word in lowered for word in words):
            return key
    return "default"


def room_id(room_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (room_name or "").lower()).strip("-")
    return slug or "unknown"


def expand_merged_cells(rows: Iterable[list[str]]) -> list[list[str]]:
    """Carry values downwards/rightwards across vertically merged cells."""
    expanded: list[list[str]] = []
    previous: list[str] = []
    for row in rows:
        filled: list[str] = []
        for i, cell in enumerate(row):
            value = (cell or "").strip()
            if not value and i < len(previous):
                value = previous[i]
            filled.append(value)
        expanded.append(filled)
        previous = filled
    return expanded


def parse_schedule_table(
    rows: list[list[str]],
    *,
    meeting_id: str,
    date: str,
    day: str,
    source_id: str,
    contributed: list[str],
) -> list[Session]:
    """Turn one day's table (header row = rooms) into normalized sessions."""
    if not rows:
        return []

    header, *body = expand_merged_cells(rows)
    rooms = [(i, name) for i, name in enumerate(header) if i > 0 and name]
    sessions: list[Session] = []

    for row in body:
        times = parse_time_range(row[0] if row else "")
        if not times:
            continue
        start, end = times
        for index, room_name in rooms:
            if index >= len(row):
                continue
            text = row[index].strip()
            if not text:
                continue
            rid = room_id(room_name)
            sessions.append(
                Session(
                    sessionId=f"{meeting_id}-{date}-{rid}-{start.replace(':', '')}",
                    meetingId=meeting_id,
                    date=date,
                    day=day,
                    startTime=start,
                    endTime=end,
                    roomId=rid,
                    roomName=room_name,
                    topic=text.splitlines()[0][:120],
                    topicKey=topic_key_for(text),
                    agendaItems=extract_agenda_items(text),
                    kind="break" if "break" in text.lower() else "session",
                    sources=[SessionSourceRef(sourceId=source_id, contributed=contributed)],
                )
            )
    return sessions


def read_docx_tables(path: str) -> list[list[list[str]]]:
    """Read every table in a DOCX as a list of rows of cell strings."""
    from docx import Document  # imported lazily so tests can run without python-docx

    document = Document(path)
    return [[[cell.text for cell in row.cells] for row in table.rows] for table in document.tables]
