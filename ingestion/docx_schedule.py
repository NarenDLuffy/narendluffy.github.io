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

from .models import AgendaSlot, Room, ScheduleSource, Session, SessionSourceRef

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
TIME_RANGE_RE = re.compile(r"(\d{1,2})[:.](\d{2})\s*(?:~|-|–|—|to)\s*(\d{1,2})[:.](\d{2})")
DURATION_RE = re.compile(r"\(\s*\d+\s*(?:min|mins|minutes)?\s*\)", re.I)
AGENDA_RE = re.compile(r"\b\d{1,2}(?:\.\d+[a-z]?)+\b")
AI_RE = re.compile(r"\bAI\s*(\d{1,2}(?:\.\d+)*)", re.I)
ROOM_RE = re.compile(r"(?:room\s*[:\-]\s*|@\s*)([^)\n]+)", re.I)
OWNER_RE = re.compile(r"([A-Z][A-Za-z\-]+)(?:'|’)s\b")
CELL_LEAD_RE = re.compile(r"^([A-Z][a-z]+)\s*(?:\(|,|:|$)")
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


MINUTES_RE = re.compile(r"\(\s*(\d{1,3})\s*(?:min|mins|minutes)?\s*\)")


def _add_minutes(hhmm: str, minutes: int) -> str:
    total = int(hhmm[:2]) * 60 + int(hhmm[3:]) + minutes
    return f"{(total // 60) % 24:02d}:{total % 60:02d}"


def _breakdown(text: str, block_start: str, block_end: str) -> list[AgendaSlot]:
    """Per-agenda-item split of a block: "6GR (120) / .10.5.1.3(30) / ..."."""
    slots: list[AgendaSlot] = []
    block_minutes = (
        int(block_end[:2]) * 60 + int(block_end[3:]) - int(block_start[:2]) * 60 - int(block_start[3:])
    )
    for line in text.split("\n"):
        line = line.strip().lstrip(".").strip()
        if not line or BREAK_RE.search(line):
            continue
        minutes_match = MINUTES_RE.search(line)
        codes = _agenda_items(line)
        if not codes and not minutes_match:
            continue
        label = MINUTES_RE.sub("", line).strip(" .:-–/")
        slots.append(
            AgendaSlot(
                code=codes[0] if codes else None,
                label=label or (codes[0] if codes else line),
                minutes=int(minutes_match.group(1)) if minutes_match else None,
            )
        )
    # A first line stating the whole block length is the block header, not a part.
    if len(slots) > 1 and slots[0].minutes == block_minutes:
        slots = slots[1:]
    # Chairs often write the release on its own line above the topic with the
    # same duration ("R20 (40)" then "NTN-NR (40)"): that is one slot, not two.
    merged: list[AgendaSlot] = []
    index = 0
    while index < len(slots):
        current = slots[index]
        nxt = slots[index + 1] if index + 1 < len(slots) else None
        if (
            nxt is not None
            and current.code is None
            and current.minutes is not None
            and current.minutes == nxt.minutes
        ):
            nxt.label = f"{current.label} {nxt.label}".strip()
            merged.append(nxt)
            index += 2
            continue
        merged.append(current)
        index += 1
    slots = merged
    if len(slots) < 2 and not any(s.minutes for s in slots):
        return []
    # Lay the parts out back-to-back from the start of the block.
    cursor = block_start
    for slot in slots:
        if slot.minutes is None:
            continue
        end = _add_minutes(cursor, slot.minutes)
        if end > block_end:
            break
        slot.startTime, slot.endTime = cursor, end
        cursor = end
    return slots


def _topic(text: str) -> str:
    """First line of the cell that actually names a topic."""
    for line in text.split("\n"):
        cleaned = TIME_RANGE_RE.sub("", line)
        cleaned = DURATION_RE.sub("", cleaned)
        cleaned = re.sub(r"\(\s*\d+\s*\)", "", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" .:-–/")
        if cleaned and not AGENDA_RE.fullmatch(cleaned):
            return cleaned
    return "Session"


def _topic_key(topic: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    return key[:40] or "session"


_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_MC_NS = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
_WP_NS = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"


def _floating_labels(paragraph: Paragraph) -> list[tuple[int, str]]:
    """Room labels chairs draw as floating text boxes above a schedule table.

    Returns (horizontal offset, label) pairs so the caller can map them onto
    the parallel columns of the table that follows.
    """
    labels: list[tuple[int, str]] = []
    for anchor in paragraph._p.iter(f"{_MC_NS}AlternateContent"):
        raw = "".join(t.text or "" for t in anchor.iter(f"{_W_NS}t")).strip()
        if not raw:
            continue
        # The same text appears in both mc:Choice and mc:Fallback.
        if len(raw) % 2 == 0 and raw[: len(raw) // 2] == raw[len(raw) // 2 :]:
            raw = raw[: len(raw) // 2]
        raw = re.sub(r"\s+", " ", raw).strip()
        if not raw or len(raw) > 60:
            continue
        offset = 0
        pos_h = anchor.find(f".//{_WP_NS}positionH")
        if pos_h is not None:
            node = pos_h.find(f"{_WP_NS}posOffset")
            if node is not None and node.text:
                offset = int(node.text)
        labels.append((offset, raw))
    return labels


def parse_schedule_docx(

    path: str,
    *,
    meeting_id: str,
    start_date: str,
    end_date: str,
    source: ScheduleSource,
    room_order_offset: int = 0,
    owner_hint: str | None = None,
) -> tuple[list[Room], list[Session]]:
    """Rooms and sessions contained in one schedule document."""
    document = docx.Document(path)
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    by_weekday = _weekday_dates(start, end)

    rooms: dict[str, Room] = {}
    sessions: list[Session] = []
    heading = ""
    pending_labels: list[str] = []

    for block in _iter_blocks(document):
        if isinstance(block, Paragraph):
            pending_labels.extend(_floating_labels(block))
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
            owner_hint=owner_hint,
            lane_labels=pending_labels,
        )
        pending_labels = []
        for room in table_rooms:
            rooms.setdefault(room.roomId, room)
        sessions.extend(table_sessions)


    return list(rooms.values()), sessions


def _room_label(
    heading: str, source_label: str, owner_hint: str | None = None
) -> tuple[str, str | None]:
    """(track name, session lead) inferred from the table heading.

    Chairs name a physical room when they have one ("room: RAN1_Brk#2",
    "@Praetorium"); otherwise the table is that chair's online or offline
    track, named after the chair so a delegate knows where to go.
    """
    m = ROOM_RE.search(heading)
    lead_match = OWNER_RE.search(heading)
    lead = lead_match.group(1) if lead_match else owner_hint
    if m:
        room = re.sub(r"\s*,\s*", " · ", m.group(1).strip())
        return room, lead
    lowered = heading.lower()
    for mode in ("offline", "online"):
        if mode in lowered:
            return (f"{lead}'s {mode} sessions" if lead else f"{mode.capitalize()} sessions"), lead
    label = re.sub(r"^RAN1#\d+[-\w]*\s*", "", heading or source_label).strip()
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
    owner_hint: str | None = None,
    lane_labels: list[tuple[int, str]] | None = None,
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

    base_name, lead = _room_label(heading, source.label, owner_hint)

    # Chairs often name the physical rooms in floating text boxes drawn above
    # the parallel columns. When there is one label per parallel column, each
    # column is that room; otherwise the whole table is one track.
    lanes = max(per_day_seen.values()) if per_day_seen else 1
    named_lanes: dict[int, str] = {}
    if lane_labels and len(lane_labels) == lanes and lanes > 1:
        for lane_index, (_, name) in enumerate(sorted(lane_labels, key=lambda x: x[0])):
            named_lanes[lane_index] = name

    def _room_for(lane: int) -> Room:
        name = named_lanes.get(lane, base_name)
        room_id = f"{meeting_id}-{_short_hash(name if lane in named_lanes else source.sourceId + heading)}"
        existing = rooms_by_id.get(room_id)
        if existing:
            return existing
        room = Room(
            roomId=room_id,
            meetingId=meeting_id,
            roomName=name,
            order=order_offset + lane,
            shortName=name[:24],
            description=heading or None,
        )
        rooms_by_id[room_id] = room
        return room

    rooms_by_id: dict[str, Room] = {}



    sessions: list[Session] = []
    seen: set[str] = set()
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
            if cell_index > 0 and cells[cell_index]._tc is cells[cell_index - 1]._tc:
                continue  # horizontally merged: already emitted in its first column
            text = _cell_text(cells[cell_index])
            if not text or SKIP_CELL_RE.match(text):
                continue
            override = _parse_range(text.split("\n", 1)[0])
            start_time, end_time = override or slot
            if end_time <= start_time:
                continue
            topic = _topic(text)
            cell_lead = None
            lead_match = CELL_LEAD_RE.match(topic)
            if lead_match and lead_match.group(1).lower() not in ("session", "break", "lunch"):
                cell_lead = lead_match.group(1)
                remainder = topic[lead_match.end(1) :].strip(" ():,-")
                topic = remainder or _topic("\n".join(text.split("\n")[1:])) or topic
            if not topic or SKIP_CELL_RE.match(topic):
                continue
            kind = "plenary" if re.search(r"commenc|close|opening|plenary", text, re.I) else "session"
            room = _room_for(lane)
            session_id = (
                f"{meeting_id}-"
                f"{_short_hash(room.roomId, day.isoformat(), start_time, end_time, topic, str(lane))}"
            )

            if session_id in seen:
                continue  # merged cells repeat the same session across columns
            seen.add(session_id)
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
                    agendaBreakdown=_breakdown(text, start_time, end_time),
                    sessionLead=cell_lead or lead,
                    kind=kind,  # type: ignore[arg-type]
                    note="\n".join(text.split("\n")[1:])[:280] or None,
                    sources=[SessionSourceRef(sourceId=source.sourceId, contributed=["all"])],
                )
            )

    used = {s.roomId for s in sessions}
    return [r for r in rooms if r.roomId in used], sessions
