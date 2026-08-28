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
AGENDA_CODE_RE = re.compile(r"\b(\d{1,2}(?:\.(?:\d{1,2}|x))+)", re.I)
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
class _Slot:
    label: str
    minutes: int | None
    group: str


@dataclass
class _Segment:
    lead: str | None
    group: str
    minutes: int | None
    slots: list[_Slot]
    raw: str


def _is_group_token(label: str) -> bool:
    token = label.strip().strip(".").lower()
    return token in GROUP_TOKENS


BARE_CODE_RE = re.compile(r"^\.?\d{1,2}(?:\.(?:\d{1,2}|x))+$", re.I)


def _code_list(line: str) -> list[str]:
    """["9.3.3", "9.3.1"] for a line that is only a list of agenda items.

    Sub-chairs often write the item order under a headed block without giving
    each item its own duration ("R20 A-IoT (120)" / "9.3.3, 9.3.1, 9.3.2").
    Those codes are the detail of that block and must not be mistaken for a
    work-area tag, otherwise the block stays undetailed.
    """
    parts = [p.strip(" .·-") for p in re.split(r"[,;/]", line) if p.strip(" .·-")]
    if len(parts) < 1 or not all(BARE_CODE_RE.match(p) for p in parts):
        return []
    return parts



def _parse_cell(text: str) -> list[_Segment]:
    """Split a cell into consecutive sub-blocks.

    A cell reads as a stack of headed blocks, e.g.

        Hiroki (120)
        R20
        A-IoT (60)

        6GR
        .10.8.x Sensing (60)

    The head ("Hiroki (120)") owns the whole 120 minutes; the lines below it are
    the agenda items sharing that time, each tagged with the work-area label
    that precedes it ("R20", "6GR"). A blank line does *not* end the head block
    while the head still has unallocated minutes — chairs use it to separate two
    work areas inside the same session.
    """
    lines: list[str] = []
    for raw_line in text.split("\n"):
        stripped = raw_line.strip()
        if not stripped:
            continue
        # "R20 (80)AI/ML (80)" is two stacked labels typed on one line.
        if len(re.findall(r"\(\s*~?\s*\d{1,3}[^)]*\)", stripped)) > 1:
            lines.extend(
                part.strip()
                for part in re.split(r"(?<=\))\s*(?=[A-Za-z.])", stripped)
                if part.strip()
            )
        else:
            lines.append(stripped)

    segments: list[_Segment] = []
    current: _Segment | None = None
    current_group = ""
    allocated = 0

    def finished() -> bool:
        """True when the open block can take no more items."""
        if current is None:
            return True
        if current.minutes is None:
            # A head without its own duration (a plenary note, a bare tag) ends
            # as soon as a timed head follows it.
            return True
        return allocated >= current.minutes

    def tag_finished() -> bool:
        if current is None:
            return True
        if current.minutes is None:
            return bool(current.slots)
        return allocated >= current.minutes

    for line in lines:
        codes = _code_list(line)
        if codes and current is not None:
            # "9.3.3, 9.3.1, 9.3.2" under a head is the ordered list of agenda
            # items sharing that head's time, not a work-area tag.
            for code in codes:
                current.raw += "\n" + code
                current.slots.append(
                    _Slot(label=code, minutes=None, group=current_group or current.group)
                )
            continue

        label, minutes = _split_head(line)
        if not label:
            continue
        is_item = line.startswith(".")
        heads_new = not is_item and (_looks_like_person(label) or _is_group_token(label))

        if not is_item and minutes is None:
            # Bare work-area tag: labels the items that follow.
            if current is None or (tag_finished() and not _looks_like_person(label)):
                current = _Segment(lead=None, group=label, minutes=None, slots=[], raw=line)
                segments.append(current)
                current_group, allocated = label, 0
            else:
                current_group = label
                current.raw += "\n" + line
            continue


        if current is None or (heads_new and finished()):
            lead = label if _looks_like_person(label) else None
            current = _Segment(
                lead=lead,
                group="" if lead else label,
                minutes=minutes,
                slots=[],
                raw=line,
            )
            segments.append(current)
            current_group = "" if lead else label
            allocated = 0
            continue

        current.raw += "\n" + line
        current.slots.append(_Slot(label=label, minutes=minutes, group=current_group or current.group))

        if minutes:
            allocated += minutes

    return segments



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

        def room_for(day_start: int, day_end: int, col_start: int, rank: int, count: int) -> Room:
            width = max(1, day_end - day_start)
            offset = max(0, col_start - day_start)
            if labels and count == len(labels):
                # Cells split the day evenly across the named rooms.
                index = rank
            else:
                # Uneven merges: place the cell by where it sits in the day.
                index = min(len(labels) - 1, offset * len(labels) // width) if labels else offset
            if labels and 0 <= index < len(labels):
                name = labels[index]
            elif labels:
                name = f"Breakout {index + 1}"
            elif width == 1 and _heading_room(heading, known_labels):
                # "Detailed schedule for … @Praetorium" is that room's column,
                # not a separate track.
                name = _heading_room(heading, known_labels) or ""
            else:
                base = re.sub(r"^RAN1#?\d+\s*", "", heading).strip() or f"Track {table_index}"
                base = re.sub(r"\s*(schedule|sessions?|for)\s*$", "", base, flags=re.I).strip() or base
                name = base if count <= 1 else f"{base} {index + 1}"

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

            for day, (day_start, day_end) in days.items():
                if day not in day_dates:
                    continue
                in_day = [
                    cell
                    for cell in cells[1:]
                    if cell.col_start < day_end and cell.col_end > day_start
                ]
                in_day.sort(key=lambda cell: cell.col_start)
                for rank, cell in enumerate(in_day):
                    if not cell.text.strip():
                        continue
                    room = room_for(day_start, day_end, cell.col_start, rank, len(in_day))
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

    def seg_length(seg: _Segment) -> int | None:
        slot_sum = sum(slot.minutes or 0 for slot in seg.slots)
        if seg.minutes and slot_sum:
            return max(seg.minutes, slot_sum)
        return seg.minutes or slot_sum or None

    lengths = [seg_length(seg) for seg in segments]
    unknown = [i for i, length in enumerate(lengths) if not length]
    remaining_default = max(0, total - sum(length or 0 for length in lengths)) // len(unknown) if unknown else 0

    out: list[Session] = []
    cursor = block_start
    for segment, known_length in zip(segments, lengths):
        length = known_length or remaining_default or max(0, block_end - cursor)
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
        sized = [slot.minutes for slot in segment.slots if slot.minutes]
        fallback = (
            max(5, (span - sum(sized)) // max(1, len(segment.slots) - len(sized)))
            if len(segment.slots) > len(sized)
            else 0
        )
        for slot in segment.slots:
            length = slot.minutes or fallback or max(5, span // len(segment.slots))
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
                    title=slot.label,
                    group=slot.group or segment.group,
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
