"""Parser for the "online and offline schedules" grid used by RAN1 chairs.

The document is one table per session family (online / offline / main), laid
out as a week grid:

    ┌────────────┬───────── Monday ─────────┬───── Tuesday ─────┬ …
    │ 08:30 ~    │  room A  │ room B │ room │  …
    │ 10:30      │  cell    │ cell   │ cell │
    ├────────────┴──────────────────────────┴───────────────────┴ …
    │ Morning coffee break: 10:30 ~ 11:00                          │

Rows are fixed time blocks, day columns are split into one column per parallel
room, and the physical room names are floating text boxes anchored above the
table (their horizontal offset gives the column order). Nothing here is
specific to one meeting: days, blocks, rooms and topics are all read from the
document.

A cell holds one or more consecutive sub-sessions, e.g.

    6GR (120)
    .10.5.1.3(30)
    .10.5.1.2(30)
    .10.5.1.1(60)

which is published as three sessions running back to back inside the block, so
the timetable shows how much of a two hour block each agenda item gets.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, timedelta

from docx import Document

from .models import AgendaSlot, Room, ScheduleSource, Session, SessionSourceRef

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

TIME_RE = re.compile(r"(\d{1,2})[:.](\d{2})")
BLOCK_RE = re.compile(r"(\d{1,2})[:.](\d{2})\s*(?:~|-|–|to)\s*(\d{1,2})[:.](\d{2})")
BREAK_RE = re.compile(r"\b(break|lunch|coffee)\b", re.I)
DURATION_RE = re.compile(r"\(\s*~?\s*(\d{1,3})\s*(?:min|mins|minutes)?\s*\)\s*$", re.I)
TBD_RE = re.compile(r"\(\s*(tbd|n/?a)\s*\)\s*$", re.I)
AGENDA_CODE_RE = re.compile(r"\b(\d{1,2}(?:\.\d{1,2})+(?:\.x)?)", re.I)
STARTS_AT_RE = re.compile(r"\bat\s+(\d{1,2})[:.](\d{2})", re.I)

# Short work-area labels chairs use as a group tag rather than a person.
GROUP_TOKENS = {
    "6gr", "6g", "r20", "r19", "r18", "nr", "lte", "tei", "ai", "ai/ml", "aiml",
    "ntn", "ntn-nr", "ntn-iot", "a-iot", "isac", "mimo", "sweep", "plenary",
}


def _minutes(text: str) -> int:
    hour, minute = text.split(":")
    return int(hour) * 60 + int(minute)


def _hhmm(total: int) -> str:
    total = max(0, min(total, 24 * 60 - 1))
    return f"{total // 60:02d}:{total % 60:02d}"


def _slug(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:8]


@dataclass
class _Cell:
    text: str
    col_start: int
    col_end: int


def _cell_text(tc) -> str:
    """Paragraph text of a cell, blank paragraphs preserved as separators."""
    lines: list[str] = []
    for p in tc.findall(f"{W}p"):
        lines.append("".join(t.text or "" for t in p.iter(f"{W}t")).strip())
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _row_cells(tr) -> list[_Cell]:
    cells: list[_Cell] = []
    cursor = 0
    for tc in tr.findall(f"{W}tc"):
        pr = tc.find(f"{W}tcPr")
        span = 1
        if pr is not None:
            gs = pr.find(f"{W}gridSpan")
            if gs is not None:
                span = int(gs.get(f"{W}val"))
        cells.append(_Cell(_cell_text(tc), cursor, cursor + span))
        cursor += span
    return cells


def _room_labels_before(paragraph) -> list[str]:
    """Floating room labels anchored in a paragraph, left to right."""
    labels: list[tuple[int, str]] = []
    for anchor in paragraph.iter():
        if not (anchor.tag.endswith("}anchor") or anchor.tag.endswith("}inline")):
            continue
        text = ""
        for box in anchor.iter():
            if box.tag.endswith("}txbxContent"):
                text = " ".join(
                    "".join(t.text or "" for t in p.iter(f"{W}t")).strip()
                    for p in box.iter(f"{W}p")
                ).strip()
                if text:
                    break
        if not text:
            continue
        offsets = [e for e in anchor.iter() if e.tag.endswith("}posOffset")]
        x = int(offsets[0].text) if offsets and offsets[0].text else 0
        labels.append((x, text))
    ordered: list[str] = []
    for _, text in sorted(labels, key=lambda pair: pair[0]):
        if text not in ordered:
            ordered.append(text)
    return ordered


def _paragraph_text(paragraph) -> str:
    """Plain paragraph text, excluding anything inside floating text boxes."""
    boxed = {id(t) for box in paragraph.iter() if box.tag.endswith("}txbxContent") for t in box.iter(f"{W}t")}
    return "".join(t.text or "" for t in paragraph.iter(f"{W}t") if id(t) not in boxed).strip()


def _heading_room(heading: str, known: list[str]) -> str | None:
    """A room the heading refers to, when it names one already seen."""
    lowered = heading.lower()
    for label in known:
        if label.lower() in lowered:
            return label
    return None


def _looks_like_person(label: str) -> bool:
    token = label.strip().strip(".")
    if not token or " " in token or any(ch.isdigit() for ch in token):
        return False
    return token.lower() not in GROUP_TOKENS and token[:1].isupper()


def _split_head(line: str) -> tuple[str, int | None]:
    """"6GR (120)" → ("6GR", 120); "TEI (TBD)" → ("TEI", None)."""
    match = DURATION_RE.search(line)
    if match:
        return line[: match.start()].strip(" .·-"), int(match.group(1))
    if TBD_RE.search(line):
        return TBD_RE.sub("", line).strip(" .·-"), None
    return line.strip(" .·-"), None


@dataclass
class _Segment:
    lead: str | None
    group: str
    minutes: int | None
    slots: list[tuple[str, int | None]]
    raw: str


def _parse_cell(text: str) -> list[_Segment]:
    """Split a cell into consecutive sub-blocks.

    A blank line always separates sub-blocks. Chairs also stack them without a
    blank line, so a line that names a work area or a person *and* carries its
    own duration starts a new sub-block once the current one is complete.
    """
    segments: list[_Segment] = []
    chunks: list[list[str]] = []
    for chunk in re.split(r"\n\s*\n", text):
        lines = [line.strip() for line in chunk.split("\n") if line.strip()]
        if not lines:
            continue
        # A chunk that opens with an agenda item continues the previous block:
        # chairs often leave a blank line between items of the same session.
        if chunks and lines[0].startswith("."):
            chunks[-1].extend(lines)
        else:
            chunks.append(lines)
    for lines in chunks:
        for group_lines in _split_stacked(lines):
            segments.append(_segment_from_lines(group_lines))
    return segments


def _split_stacked(lines: list[str]) -> list[list[str]]:
    groups: list[list[str]] = []
    current: list[str] = []
    head_minutes: int | None = None
    slot_minutes = 0
    for line in lines:
        label, minutes = _split_head(line)
        is_item = line.startswith(".")
        if current and minutes is not None and not is_item:
            heads_new = _looks_like_person(label) or label.lower() in GROUP_TOKENS
            finished = head_minutes is None or (slot_minutes and slot_minutes >= head_minutes)
            if heads_new and finished:
                groups.append(current)
                current, head_minutes, slot_minutes = [line], minutes, 0
                continue
        if not current:
            current, head_minutes, slot_minutes = [line], minutes, 0
            continue
        current.append(line)
        if minutes is not None:
            slot_minutes += minutes
    if current:
        groups.append(current)
    return groups


def _segment_from_lines(lines: list[str]) -> _Segment:
    head, head_minutes = _split_head(lines[0])
    lead = head if _looks_like_person(head) else None
    group_parts: list[str] = [] if lead else [head]
    slots: list[tuple[str, int | None]] = []
    for line in lines[1:]:
        label, minutes = _split_head(line)
        if not label:
            continue
        if minutes is None and not line.startswith("."):
            group_parts.append(label)
        else:
            slots.append((label, minutes))
    group = " ".join(part for part in group_parts if part).strip()
    return _Segment(
        lead=lead,
        group=group or (head if not lead else ""),
        minutes=head_minutes,
        slots=slots,
        raw="\n".join(lines),
    )


def _day_columns(header_cells: list[_Cell]) -> dict[str, tuple[int, int]]:
    days: dict[str, tuple[int, int]] = {}
    for cell in header_cells:
        lowered = cell.text.lower()
        for day in DAY_NAMES:
            if day.lower() in lowered and day not in days:
                days[day] = (cell.col_start, cell.col_end)
    return days


def parse_block_schedule_docx(
    path: str,
    *,
    meeting_id: str,
    start_date: str,
    end_date: str,
    source: ScheduleSource,
    room_order_offset: int = 0,
) -> tuple[list[Room], list[Session]]:
    """Parse a week-grid schedule document into rooms and sessions.

    Returns empty lists when the document is not in this format, so callers can
    fall back to another parser.
    """
    document = Document(path)
    body = document.element.body
    meeting_start = date.fromisoformat(start_date)
    meeting_end = date.fromisoformat(end_date)
    day_dates: dict[str, str] = {}
    cursor = meeting_start
    while cursor <= meeting_end:
        day_dates.setdefault(DAY_NAMES[cursor.weekday()], cursor.isoformat())
        cursor += timedelta(days=1)

    rooms: dict[str, Room] = {}
    known_labels: list[str] = []
    sessions: list[Session] = []
    breaks: dict[tuple[str, str, str], Session] = {}
    pending_labels: list[str] = []
    pending_heading = ""
    table_index = 0

    for child in body:
        tag = child.tag.split("}")[1]
        if tag == "p":
            labels = _room_labels_before(child)
            if labels:
                pending_labels = labels
            heading = _paragraph_text(child)
            if heading:
                pending_heading = heading
            continue
        if tag != "tbl":
            continue

        rows = child.findall(f"{W}tr")
        if not rows:
            continue
        header = _row_cells(rows[0])
        days = _day_columns(header)
        labels = pending_labels
        for label in labels:
            if label not in known_labels:
                known_labels.append(label)
        heading = pending_heading
        pending_labels, pending_heading = [], ""
        table_index += 1
        if not days:
            continue

        def room_for(day_start: int, day_end: int, col_start: int, col_end: int) -> Room:
            index = max(0, col_start - day_start)
            width = max(1, day_end - day_start)
            if index < len(labels):
                name = labels[index]
            elif len(labels) == 1 and width == 1:
                name = labels[0]
            elif labels:
                name = f"Breakout {index + 1}"
            elif width == 1 and _heading_room(heading, known_labels):
                # "Detailed schedule for … @Praetorium" is that room's column,
                # not a separate track.
                name = _heading_room(heading, known_labels) or ""
            else:
                base = re.sub(r"^RAN1#?\d+\s*", "", heading).strip() or f"Track {table_index}"
                base = re.sub(r"\s*(schedule|sessions?|for)\s*$", "", base, flags=re.I).strip() or base
                name = base if width == 1 else f"{base} {index + 1}"
            room_id = f"{meeting_id}-room-{_slug(name.lower())}"
            room = rooms.get(room_id)
            if room is None:
                room = Room(
                    roomId=room_id,
                    meetingId=meeting_id,
                    roomName=name,
                    order=room_order_offset + len(rooms),
                )
                rooms[room_id] = room
            return room

        for row in rows[1:]:
            cells = _row_cells(row)
            if not cells:
                continue
            label_text = cells[0].text.replace("\n", " ")

            # Full-width break band (checked first: it also carries a time range).
            joined = " ".join(cell.text for cell in cells).replace("\n", " ")
            if BREAK_RE.search(label_text):
                span = BLOCK_RE.search(joined)
                if span:
                    for day, day_date in day_dates.items():
                        key = (day_date, f"{span.group(1)}:{span.group(2)}", label_text[:40])
                        if key in breaks:
                            continue
                        title = label_text.split(":")[0].strip() or "Break"
                        breaks[key] = Session(
                            sessionId=f"{meeting_id}-break-{_slug(day_date + title)}",
                            meetingId=meeting_id,
                            date=day_date,
                            day=day,
                            startTime=_hhmm(_minutes(f"{span.group(1)}:{span.group(2)}")),
                            endTime=_hhmm(_minutes(f"{span.group(3)}:{span.group(4)}")),
                            roomId="",
                            roomName="",
                            topic=title,
                            topicKey="break",
                            kind="lunch" if "lunch" in title.lower() else "break",
                            sources=[SessionSourceRef(source.sourceId, ["break"])],
                        )
                continue
            block = BLOCK_RE.search(label_text)
            if not block:
                continue

            block_start = _minutes(f"{block.group(1)}:{block.group(2)}")
            block_end = _minutes(f"{block.group(3)}:{block.group(4)}")

            for cell in cells[1:]:
                if not cell.text.strip():
                    continue
                day = next(
                    (
                        name
                        for name, (col_start, col_end) in days.items()
                        if cell.col_start < col_end and cell.col_end > col_start
                    ),
                    None,
                )
                if day is None or day not in day_dates:
                    continue
                day_start, day_end = days[day]
                room = room_for(day_start, day_end, cell.col_start, cell.col_end)
                sessions.extend(
                    _sessions_for_cell(
                        cell.text,
                        meeting_id=meeting_id,
                        day=day,
                        day_date=day_dates[day],
                        room=room,
                        block_start=block_start,
                        block_end=block_end,
                        source=source,
                    )
                )

    sessions = [s for s in sessions if s.startTime < s.endTime]
    # The same slot written twice (a chair repeating the plenary or their own
    # column in a detail table) is one session.
    unique: dict[tuple[str, str, str, str], Session] = {}

    def informative(session: Session) -> tuple[int, int, int]:
        topic = session.topic.strip()
        return (
            0 if topic.lower().startswith("ai ") else 1,  # drop bare "AI <x>" labels
            len(session.agendaItems),
            len(topic),
        )

    for session in sessions:
        key = (session.date, session.startTime, session.endTime, session.roomId)
        current = unique.get(key)
        if current is None or informative(session) > informative(current):
            unique[key] = session
    sessions = list(unique.values())
    if not sessions:
        return [], []
    return sorted(rooms.values(), key=lambda r: r.order), [*sessions, *breaks.values()]


def _sessions_for_cell(
    text: str,
    *,
    meeting_id: str,
    day: str,
    day_date: str,
    room: Room,
    block_start: int,
    block_end: int,
    source: ScheduleSource,
) -> list[Session]:
    segments = _parse_cell(text)
    if not segments:
        return []

    total = block_end - block_start
    known = [seg.minutes for seg in segments if seg.minutes]
    remaining_default = max(0, total - sum(known)) // max(1, len(segments) - len(known)) if len(segments) > len(known) else 0

    out: list[Session] = []
    cursor = block_start
    for segment in segments:
        length = segment.minutes or remaining_default or (block_end - cursor)
        seg_start = cursor
        seg_end = min(block_end, seg_start + length)
        cursor = seg_end

        explicit = STARTS_AT_RE.search(segment.raw)
        if explicit and not segment.slots:
            seg_start = _minutes(f"{explicit.group(1)}:{explicit.group(2)}")
            seg_end = min(block_end, seg_start + (segment.minutes or 60))
            cursor = max(cursor, seg_end)

        if not segment.slots:
            title = segment.group or segment.lead or segment.raw.split("\n")[0]
            body = [line for line in segment.raw.split("\n")[1:] if line.strip()]
            out.append(
                _make_session(
                    meeting_id=meeting_id,
                    day=day,
                    day_date=day_date,
                    room=room,
                    start=seg_start,
                    end=seg_end,
                    title=title,
                    group=segment.group,
                    lead=segment.lead,
                    note="\n".join(body) or None,
                    source=source,
                )
            )
            continue

        # Each agenda item gets its own share of the block, back to back.
        slot_cursor = seg_start
        span = seg_end - seg_start
        sized = [minutes for _, minutes in segment.slots if minutes]
        fallback = max(5, (span - sum(sized)) // max(1, len(segment.slots) - len(sized))) if len(segment.slots) > len(sized) else 0
        for label, minutes in segment.slots:
            length = minutes or fallback or max(5, span // len(segment.slots))
            slot_start = slot_cursor
            slot_end = min(block_end, slot_start + length)
            slot_cursor = slot_end
            if slot_end <= slot_start:
                break
            out.append(
                _make_session(
                    meeting_id=meeting_id,
                    day=day,
                    day_date=day_date,
                    room=room,
                    start=slot_start,
                    end=slot_end,
                    title=label,
                    group=segment.group,
                    lead=segment.lead,
                    note=None,
                    source=source,
                )
            )
    return out


def _make_session(
    *,
    meeting_id: str,
    day: str,
    day_date: str,
    room: Room,
    start: int,
    end: int,
    title: str,
    group: str,
    lead: str | None,
    note: str | None,
    source: ScheduleSource,
) -> Session:
    clean = re.sub(r"\s+", " ", title).strip(" .·-") or group or "Session"
    codes = AGENDA_CODE_RE.findall(clean)
    label = AGENDA_CODE_RE.sub("", clean).strip(" .·-") if codes else clean
    kind = "plenary" if re.search(r"commences|plenary|closing|session reports", clean, re.I) else "session"
    group_label = re.sub(r"\s+", " ", group).strip() or (codes[0].split(".")[0] if codes else clean)
    return Session(
        sessionId=f"{meeting_id}-{_slug(f'{day_date}{start}{room.roomId}{clean}')}",
        meetingId=meeting_id,
        date=day_date,
        day=day,
        startTime=_hhmm(start),
        endTime=_hhmm(end),
        roomId=room.roomId,
        roomName=room.roomName,
        topic=label or clean,
        topicKey=_slug(group_label.lower()),
        agendaItems=codes,
        agendaBreakdown=[
            AgendaSlot(
                code=codes[0] if codes else None,
                label=label or clean,
                minutes=end - start,
                startTime=_hhmm(start),
                endTime=_hhmm(end),
            )
        ],
        sessionLead=lead,
        group=group_label or None,
        kind=kind,  # type: ignore[arg-type]
        note=note,
        sources=[SessionSourceRef(source.sourceId, ["time", "topic", "room"])],
    )
