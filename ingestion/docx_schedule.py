"""Generic parser for RAN1 session-schedule DOCX grids.

RAN1 chairs and vice-chairs publish their session plans as Word tables shaped
like a week grid: the header row carries weekday names, the first column carries
time slots, and every other cell describes one session (topic, agenda items and
often an explicit time range).

The parser is deliberately structural, never name-based: it looks for weekday
headers and time patterns, so any chair's document for any meeting works.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timedelta

import docx
from docx.document import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph

from .models import Room, ScheduleSource, Session, SessionSourceRef

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
TIME_RANGE_RE = re.compile(r"(\d{1,2})[:.](\d{2})\s*(?:~|-|–|—|to)\s*(\d{1,2})[:.](\d{2})")
DURATION_RE = re.compile(r"\(\s*\d+\s*(?:min|mins|minutes)?\s*\)", re.I)
AGENDA_RE = re.compile(r"\b\d{1,2}(?:\.\d+[a-z]?)+\b")
AI_RE = re.compile(r"\bAI\s*(\d{1,2}(?:\.\d+)*)", re.I)
ROOM_RE = re.compile(r"(?:room\s*[:：]\s*|@\s*)([^),.]+)", re.I)
OWNER_RE = re.compile(r"([A-Z][A-Za-z\-]+)(?:'|’)s\b")
BREAK_RE = re.compile(r"\b(break|lunch)\b", re.I)
SKIP_CELL_RE = re.compile(r"^\s*(tbd|n/?a|to be (assigned|decided)\b.*|-|–)\s*$", re.I)


def _short_hash(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:10]


def _iter_blocks(document: DocxDocument):
    body = document.element.body
    for child in body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, document)
        elif child.tag.endswith("}tbl"):
            yield Table(child, document)


def _cell_text(cell) -> str:
    lines = [p.text.strip() for p in cell.paragraphs]
    return "\n".join(line for line in lines if line).strip()


def _weekday_dates(start: date, end: date) -> dict[str, date]:
    mapping: dict[str, date] = {}
    day = start
    while day <= end:
        mapping.setdefault(WEEKDAYS[day.weekday()], day)
        day += timedelta(days=1)
    return mapping


def _parse_range(text: str) -> tuple[str, str] | None:
    m = TIME_RANGE_RE.search(text.replace("\n", " "))
    if not m:
        return None
    return (f"{int(m.group(1)):02d}:{m.group(2)}", f"{int(m.group(3)):02d}:{m.group(4)}")


def _agenda_items(text: str) -> list[str]:
    codes: list[str] = []
    for m in AI_RE.finditer(text):
        codes.append(m.group(1))
    for code in AGENDA_RE.findall(text):
        codes.append(code.lstrip("."))
    seen: list[str] = []
    for code in codes:
        code = code.strip(" .")
        if code and code not in seen:
            seen.append(code)
    return seen


def _topic(text: str) -> str:
    first = text.split("\n", 1)[0]
    first = TIME_RANGE_RE.sub("", first)
    first = DURATION_RE.sub("", first)
    first = re.sub(r"\(\s*\d+\s*\)", "", first)
    first = first.strip(" .:-–/")
    return re.sub(r"\s{2,}", " ", first) or "Session"


def _topic_key(topic: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    return key[:40] or "session"


def parse_schedule_docx(
    path: str,
    *,
    meeting_id: str,
    start_date: str,
    end_date: str,
    source: ScheduleSource,
    room_order_offset: int = 0,
) -> tuple[list[Room], list[Session]]:
    """Rooms and sessions contained in one schedule document."""
    document = docx.Document(path)
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    by_weekday = _weekday_dates(start, end)

    rooms: dict[str, Room] = {}
    sessions: list[Session] = []
    heading = ""

    for block in _iter_blocks(document):
        if isinstance(block, Paragraph):
            if block.text.strip():
                heading = block.text.strip()
            continue

        table_rooms, table_sessions = _parse_table(
            block,
            heading=heading,
            meeting_id=meeting_id,
            by_weekday=by_weekday,
            source=source,
            order_offset=room_order_offset + len(rooms),
        )
        for room in table_rooms:
            rooms.setdefault(room.roomId, room)
        sessions.extend(table_sessions)

    return list(rooms.values()), sessions


def _room_label(heading: str, source_label: str) -> tuple[str, str | None]:
    """(display name, session lead) inferred from the table heading."""
    m = ROOM_RE.search(heading)
    lead_match = OWNER_RE.search(heading)
    lead = lead_match.group(1) if lead_match else None
    if m:
        return m.group(1).strip(), lead
    label = heading or source_label
    label = re.sub(r"^RAN1#\d+[-\w]*\s*", "", label).strip()
    # No room named in the document: fall back to "<owner> <online|offline>",
    # which is how attendees refer to these parallel session tracks.
    kind = next((w for w in ("online", "offline", "detailed") if w in label.lower()), None)
    if lead and kind:
        return f"{lead} {kind}", lead
    label = re.sub(r"(?i)(session\s+)?schedule\b", "", label).strip(" -–—:")
    return (label or source_label)[:60], lead


def _parse_table(
    table: Table,
    *,
    heading: str,
    meeting_id: str,
    by_weekday: dict[str, date],
    source: ScheduleSource,
    order_offset: int,
) -> tuple[list[Room], list[Session]]:
    rows = table.rows
    if len(rows) < 2:
        return [], []

    header = [_cell_text(c).lower() for c in rows[0].cells]
    columns: list[tuple[int, date, int]] = []  # (cell index, date, position within day)
    per_day_seen: dict[str, int] = {}
    for idx, text in enumerate(header):
        weekday = next((d for d in WEEKDAYS if d in text), None)
        if not weekday or weekday not in by_weekday:
            continue
        position = per_day_seen.get(weekday, 0)
        per_day_seen[weekday] = position + 1
        columns.append((idx, by_weekday[weekday], position))
    if not columns:
        return [], []

    lanes = max(pos for _, _, pos in columns) + 1
    base_name, lead = _room_label(heading, source.label)

    rooms: list[Room] = []
    for lane in range(lanes):
        name = base_name if lanes == 1 else f"{base_name} {lane + 1}"
        rooms.append(
            Room(
                roomId=f"{meeting_id}-{_short_hash(name)}",
                meetingId=meeting_id,
                roomName=name,
                order=order_offset + lane,
                shortName=name[:18],
                description=heading or None,
            )
        )

    sessions: list[Session] = []
    for row in rows[1:]:
        cells = row.cells
        if not cells:
            continue
        label = _cell_text(cells[0])
        if BREAK_RE.search(label) and not _parse_range(label.split(":", 1)[-1] or ""):
            continue
        if BREAK_RE.search(label):
            continue  # break rows carry no sessions
        slot = _parse_range(label)
        if not slot:
            continue

        for cell_index, day, lane in columns:
            if cell_index >= len(cells):
                continue
            text = _cell_text(cells[cell_index])
            if not text or SKIP_CELL_RE.match(text):
                continue
            override = _parse_range(text.split("\n", 1)[0])
            start_time, end_time = override or slot
            if end_time <= start_time:
                continue
            topic = _topic(text)
            if not topic or SKIP_CELL_RE.match(topic):
                continue
            room = rooms[lane]
            kind = "plenary" if re.search(r"commenc|close|opening|plenary", text, re.I) else "session"
            session_id = f"{meeting_id}-{_short_hash(room.roomId, day.isoformat(), start_time, topic)}"
            sessions.append(
                Session(
                    sessionId=session_id,
                    meetingId=meeting_id,
                    date=day.isoformat(),
                    day=WEEKDAYS[day.weekday()].capitalize(),
                    startTime=start_time,
                    endTime=end_time,
                    roomId=room.roomId,
                    roomName=room.roomName,
                    topic=topic,
                    topicKey=_topic_key(topic),
                    agendaItems=_agenda_items(text),
                    sessionLead=lead,
                    kind=kind,  # type: ignore[arg-type]
                    note="\n".join(text.split("\n")[1:])[:280] or None,
                    sources=[SessionSourceRef(sourceId=source.sourceId, contributed=["all"])],
                )
            )

    used = {s.roomId for s in sessions}
    return [r for r in rooms if r.roomId in used], sessions
