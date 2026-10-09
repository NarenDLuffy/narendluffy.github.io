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

from .docx_active_text import active_paragraph_text
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
GENERIC_GRID_RE = re.compile(r"^\s*RAN1\s*#\s*\w+\s+(?:online|offline)(?:\s+and\s+offline)?\s+sessions?\s+schedules?\s*$", re.I)
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
    fill: str | None = None
    continued: bool = False


def _cell_text(tc) -> str:
    """Paragraph text of a cell, blank paragraphs preserved as separators."""
    lines: list[str] = []
    for p in tc.findall(f"{W}p"):
        lines.append(active_paragraph_text(p).strip())
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
        shading = pr.find(f"{W}shd") if pr is not None else None
        fill = shading.get(f"{W}fill") if shading is not None else None
        normalized_fill = fill.upper() if fill and fill.lower() not in {"auto", "none"} else None
        vm = pr.find(f"{W}vMerge") if pr is not None else None
        continued = vm is not None and vm.get(f"{W}val") != "restart"
        cells.append(_Cell(_cell_text(tc), cursor, cursor + span, normalized_fill, continued))
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
                    active_paragraph_text(p).strip()
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
    parts: list[str] = []
    for run in paragraph.iter(f"{W}r"):
        if any(parent.tag.endswith("}txbxContent") for parent in run.iterancestors()):
            continue
        parts.append(active_paragraph_text(run))
    return "".join(parts).strip()


def norm_room(name: str) -> str:
    """Comparable room identity: "Room 201 (2F)" == "201", "Yeongju B, 1F" == "Yeongju B (1F)"."""
    text = re.sub(r"\([^)]*\)", " ", name or "")
    text = re.sub(r"\b(room|rm)\b", " ", text, flags=re.I)
    text = re.sub(r"\b\d{1,2}\s*F\b", " ", text, flags=re.I)
    return re.sub(r"[^a-z0-9]+", "", text.lower())


_SESSION_LABEL_RE = re.compile(r"RAN1[\s_]*(main|brk|break(?:out)?|adhoc|ad-hoc)\s*#?\s*(\d*)", re.I)


def _session_label(text: str) -> str | None:
    match = _SESSION_LABEL_RE.search(text or "")
    if not match:
        return None
    kind = match.group(1).lower()
    if kind == "main":
        return "RAN1 Main"
    if kind.startswith("ad"):
        return f"RAN1 Adhoc{match.group(2)}"
    return f"RAN1 Brk{match.group(2)}"


def _heading_room_name(heading: str) -> str | None:
    """The physical room a one-room table's heading names, if any."""
    at = re.search(r"@\s*(.+)$", heading or "")
    if at:
        return at.group(1).strip(" -–—:·")
    paren = re.search(r"\(\s*rooms?\s*[:=]?\s*([^)]+)\)", heading or "", re.I)
    if paren:
        parts = [p.strip(" -–—:·") for p in re.split(r"[,;/]", paren.group(1)) if p.strip()]
        physical = [
            p for p in parts
            if not re.fullmatch(r"\d{1,2}\s*F", p, re.I) and not _SESSION_LABEL_RE.search(p)
        ]
        if physical:
            return physical[0]
    return None


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
    line = line.strip().rstrip(".").strip()
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


BARE_CODE_RE = re.compile(r"^\.?(\d{1,2}(?:\.(?:\d{1,2}|x))+)\.?\s*(?:\(\s*(\d{1,3})\s*\))?$", re.I)


def _code_list(line: str) -> list[tuple[str, int | None]]:
    """[("9.3.3", None), ...] for a line that is only a list of agenda items.

    Sub-chairs often write the item order under a headed block, with or without
    per-item minutes ("9.3.3, 9.3.1" or "10.8.2(40), 10.8.3(40)"). Those codes
    are the detail of that block and must not be mistaken for a work-area tag.
    """
    parts = [p.strip(" ·-") for p in re.split(r"[,;/]", line) if p.strip(" .·-")]
    out: list[tuple[str, int | None]] = []
    for part in parts:
        match = BARE_CODE_RE.match(part)
        if not match:
            return []
        out.append((match.group(1), int(match.group(2)) if match.group(2) else None))
    return out



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
            for code, code_minutes in codes:
                current.raw += "\n" + code
                current.slots.append(
                    _Slot(label=code, minutes=code_minutes, group=current_group or current.group)
                )
                if code_minutes:
                    allocated += code_minutes
            continue

        label, minutes = _split_head(line)
        if not label:
            continue
        is_item = line.startswith(".")
        # Any timed, non-item line ("R20 A-IoT (40)", "Maintenance (80)") opens
        # a new block once the previous one has used up its minutes.
        heads_new = not is_item and (
            _looks_like_person(label) or _is_group_token(label) or minutes is not None
        )

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

        if is_item and minutes and current.minutes and allocated >= current.minutes:
            # A timed item after the head's minutes are used up is the next
            # block of the same work area ("6GR (60) / .10.6.x (60) / .10.5.1.1 (60)").
            current = _Segment(lead=None, group=current_group or current.group, minutes=None, slots=[], raw=line)
            segments.append(current)
            allocated = 0
        current.raw += "\n" + line
        current.slots.append(_Slot(label=label, minutes=minutes, group=current_group or current.group))

        if minutes:
            allocated += minutes

    # A parent item can be followed by its timed descendants in the same cell:
    #   10.5.4 (120), 10.5.4.1 (50), 10.5.4.2 (25), ...
    # The parent is a container, not the first 120-minute child. Remove that
    # slot only when the following timed children are explicitly evidenced.
    for segment in segments:
        if len(segment.slots) < 2:
            continue
        first = segment.slots[0]
        parent_codes = AGENDA_CODE_RE.findall(first.label)
        if not parent_codes or first.minutes is None:
            continue
        parent = parent_codes[0]
        children = segment.slots[1:]
        if children and all(
            (codes := AGENDA_CODE_RE.findall(child.label))
            and codes[0].startswith(parent + ".")
            for child in children
        ):
            segment.slots = children
            if segment.minutes is None or segment.minutes == first.minutes:
                segment.minutes = first.minutes

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
    lane_names: dict[tuple[str, str], str] = {}
    lane_numbers: dict[str, dict[str, int]] = {}

    def schedule_mode(heading: str) -> str:
        lowered = heading.lower()
        if "offline" in lowered:
            return "offline"
        if "online" in lowered:
            return "online"
        return "main" if "main" in lowered else "session"

    def is_main_evidence(text: str, heading: str) -> bool:
        return bool(
            re.search(r"\bmain\s+session\b", heading, re.I)
            or re.search(r"\b(?:main\s+session|RAN1\s*#?\s*\d+[a-z-]*)\s+commences\b", text, re.I)
        )

    def room_for_key(key: str, *, name: str = "", fill: str | None = None, main: bool = False,
                     label: str | None = None) -> Room:
        """One canonical room per meeting-level identity (mode + colour, or name)."""
        room_id = f"{meeting_id}-room-{_slug(key)}"
        room = rooms.get(room_id)
        if room is None:
            room = Room(
                roomId=room_id,
                meetingId=meeting_id,
                roomName=name,
                order=room_order_offset + len(rooms),
                sourceColor=fill,
                chairLaneId=key,
                chairRole="main" if main else None,
            )
            rooms[room_id] = room
        if name and (not room.roomName or len(name) > len(room.roomName)):
            room.roomName = name
            room.shortName = name[:24]
        if main:
            room.chairRole = "main"
        if label and not room.sessionLabel:
            room.sessionLabel = label
        return room

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
        heading = pending_heading
        pending_labels, pending_heading = [], ""
        table_index += 1
        if not days:
            continue

        mode = "offline" if "offline" in heading.lower() else "online"
        # A chair's own table (detailed plan, personal schedule) rather than a
        # copy of the shared week grid.
        own_table = not GENERIC_GRID_RE.match(heading or "")
        single_lane = all(end - start <= 1 for start, end in days.values())

        # A few placeholder/TBD cells lose their lane fill in Word. Derive the
        # stable colour for each horizontal lane from the populated cells in
        # the whole table so one formatting omission cannot move a session to
        # another room.
        lane_fills: dict[int, dict[str, int]] = {}
        for row in rows[1:]:
            row_cells = _row_cells(row)
            for day_start, day_end in days.values():
                width = max(1, day_end - day_start)
                for cell in row_cells[1:]:
                    if not (cell.col_start < day_end and cell.col_end > day_start and cell.text.strip()):
                        continue
                    if not cell.fill or re.fullmatch(r"TBD|N/?A", cell.text.strip(), re.I):
                        continue
                    lane = min(width - 1, max(0, cell.col_start - day_start))
                    counts = lane_fills.setdefault(lane, {})
                    counts[cell.fill] = counts.get(cell.fill, 0) + 1
        preferred_fills = {lane: max(c, key=c.get) for lane, c in lane_fills.items() if c}
        ordered_fills: list[str] = []
        for lane in sorted(preferred_fills):
            if preferred_fills[lane] not in ordered_fills:
                ordered_fills.append(preferred_fills[lane])
        # The coloured room legend above the table lists rooms left to right
        # in the same order as the coloured lanes.
        fill_names: dict[str, str] = {}
        if labels and len(labels) == len(ordered_fills) and not single_lane:
            fill_names = dict(zip(ordered_fills, labels))

        # A table with one column per day is one room's own plan; the heading
        # names that room ("… @Yeongju A (1F)", "(room: RAN1_Brk#2, Yeongju B)",
        # "Detailed Schedule for RAN1 Main Session").
        lane_room: Room | None = None
        if single_lane:
            heading_name = _heading_room_name(heading)
            if re.search(r"\bmain\b", heading, re.I) and not heading_name:
                lane_room = room_for_key(f"{meeting_id}:main", name="RAN1 Main", main=True)
            elif heading_name:
                lane_room = room_for_key(
                    f"{meeting_id}:name:{norm_room(heading_name)}",
                    name=heading_name,
                    label=_session_label(heading),
                )

        def room_for(cell: _Cell, day_start: int, day_end: int) -> Room:
            if lane_room is not None:
                return lane_room
            width = max(1, day_end - day_start)
            lane = min(width - 1, max(0, cell.col_start - day_start))
            fill = cell.fill if cell.fill in ordered_fills else preferred_fills.get(lane, cell.fill)
            main = mode == "online" and is_main_evidence(cell.text, heading)
            key = f"{meeting_id}:{mode}:{fill or f'lane{lane}'}"
            return room_for_key(key, name=fill_names.get(fill or "", ""), fill=fill, main=main)

        merged_text: dict[int, str] = {}
        for row in rows[1:]:
            cells = _row_cells(row)
            if not cells:
                continue
            for cell in cells:
                # Vertically merged cells carry their text only in the first
                # row; repeat it for every time block they cover.
                if cell.continued and not cell.text.strip():
                    cell.text = merged_text.get(cell.col_start, "")
                else:
                    merged_text[cell.col_start] = cell.text
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
                if mode == "offline" and len(in_day) == 1 and len(ordered_fills) >= 2:
                    # One merged cell listing a placeholder per offline room
                    # ("To be assigned by A / To be assigned by B") is one per room.
                    only = in_day[0]
                    parts = [ln for ln in only.text.split("\n") if ln.strip()]
                    if len(parts) == len(ordered_fills) and all(
                        re.match(r"to be (assigned|decided)", ln.strip(), re.I) for ln in parts
                    ):
                        in_day = [
                            _Cell(part, only.col_start, only.col_end, fill)
                            for part, fill in zip(parts, ordered_fills)
                        ]
                for cell in in_day:
                    if not cell.text.strip():
                        continue
                    room = room_for(cell, day_start, day_end)
                    produced = _sessions_for_cell(
                            cell.text,
                            meeting_id=meeting_id,
                            day=day,
                            day_date=day_dates[day],
                            room=room,
                            block_start=block_start,
                            block_end=block_end,
                            source=source,
                        )
                    if own_table:
                        for item in produced:
                            for ref in item.sources:
                                ref.contributed = [*ref.contributed, "own-table"]
                    sessions.extend(produced)

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


RANGE_LINE_RE = re.compile(r"^\s*(\d{1,2})[:.](\d{2})\s*(?:-|–|~|to)\s*(\d{1,2})[:.](\d{2})\s*$")


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
    """Sessions for one cell. Times are never invented.

    A block is split into agenda items only when the document states minutes
    for every item and they fit inside the block. Otherwise the block stays
    whole and lists its items (with any stated minutes) without times.
    """
    common = dict(meeting_id=meeting_id, day=day, day_date=day_date, room=room, source=source)

    # Explicit sub-ranges inside the cell ("8:30 - 10:00" … "10:00 - 10:30").
    lines = text.split("\n")
    if any(RANGE_LINE_RE.match(line) for line in lines):
        chunks: list[tuple[int, int, list[str]]] = []
        for line in lines:
            match = RANGE_LINE_RE.match(line)
            if match:
                chunks.append((
                    _minutes(f"{match.group(1)}:{match.group(2)}"),
                    _minutes(f"{match.group(3)}:{match.group(4)}"),
                    [],
                ))
            elif chunks:
                chunks[-1][2].append(line)
        out: list[Session] = []
        for start, end, body in chunks:
            start, end = max(start, block_start), min(end, block_end)
            if start < end and any(line.strip() for line in body):
                out.extend(
                    _sessions_for_cell("\n".join(body), block_start=start, block_end=end, **common)
                )
        return out

    segments = _parse_cell(text)
    if not segments:
        return []

    total = block_end - block_start

    def seg_length(seg: _Segment) -> int | None:
        if seg.minutes:
            return seg.minutes
        minutes = [slot.minutes for slot in seg.slots]
        if minutes and all(minutes):
            return sum(m or 0 for m in minutes)
        return None

    lengths = [seg_length(seg) for seg in segments]
    known = sum(length or 0 for length in lengths)
    unknown = [i for i, length in enumerate(lengths) if not length]
    if len(segments) == 1:
        lengths = [min(total, lengths[0]) if lengths[0] and lengths[0] <= total else total]
        placeable = True
    else:
        placeable = known <= total and (not unknown or (len(unknown) == 1 and total - known > 0))
        if placeable and unknown:
            lengths[unknown[0]] = total - known

    if not placeable:
        # Stated minutes don't fit, or several parts have no time: one block.
        note = None
        if not unknown:
            note = f"Minutes don't add up: items total {known} min, block is {total} min."
        return [_whole_block(segments, block_start, block_end, note=note, **common)]

    out = []
    cursor = block_start
    for segment, length in zip(segments, lengths):
        seg_start = cursor
        seg_end = min(block_end, seg_start + (length or 0))
        cursor = seg_end

        explicit = STARTS_AT_RE.search(segment.raw)
        if explicit and not segment.slots:
            seg_start = _minutes(f"{explicit.group(1)}:{explicit.group(2)}")
            seg_end = min(block_end, seg_start + (segment.minutes or 60))
            cursor = max(cursor, seg_end)
        if seg_end <= seg_start:
            continue

        if not segment.slots:
            title = segment.group or segment.lead or segment.raw.split("\n")[0]
            body = [line for line in segment.raw.split("\n")[1:] if line.strip()]
            out.append(
                _make_session(
                    start=seg_start, end=seg_end, title=title, group=segment.group,
                    lead=segment.lead, note="\n".join(body) or None, **common,
                )
            )
            continue

        span = seg_end - seg_start
        stated = [slot.minutes for slot in segment.slots]
        if len(segment.slots) > 1 and all(stated) and sum(m or 0 for m in stated) <= span:
            # Every item has stated minutes and they fit: back to back.
            slot_cursor = seg_start
            for slot in segment.slots:
                slot_end = slot_cursor + (slot.minutes or 0)
                out.append(
                    _make_session(
                        start=slot_cursor, end=slot_end, title=slot.label,
                        group=slot.group or segment.group, lead=segment.lead, note=None, **common,
                    )
                )
                slot_cursor = slot_end
            continue
        if len(segment.slots) == 1:
            slot = segment.slots[0]
            out.append(
                _make_session(
                    start=seg_start, end=seg_end, title=slot.label,
                    group=slot.group or segment.group, lead=segment.lead, note=None, **common,
                )
            )
            continue
        note = None
        if all(stated):
            note = f"Minutes don't add up: items total {sum(m or 0 for m in stated)} min, block is {span} min."
        out.append(_whole_block([segment], seg_start, seg_end, note=note, **common))
    return out


def _whole_block(
    segments: list[_Segment],
    start: int,
    end: int,
    *,
    note: str | None,
    meeting_id: str,
    day: str,
    day_date: str,
    room: Room,
    source: ScheduleSource,
) -> Session:
    """One untimed block listing every agenda item it covers, in document order."""
    codes: list[str] = []
    breakdown: list[AgendaSlot] = []
    for segment in segments:
        for code in AGENDA_CODE_RE.findall(segment.group or ""):
            if code not in codes:
                codes.append(code)
        for slot in segment.slots:
            slot_codes = AGENDA_CODE_RE.findall(slot.label)
            for code in slot_codes:
                if code not in codes:
                    codes.append(code)
            label = AGENDA_CODE_RE.sub("", slot.label).strip(" .·-") or slot.label
            breakdown.append(
                AgendaSlot(code=slot_codes[0] if slot_codes else None, label=label, minutes=slot.minutes)
            )
    first = segments[0]
    title = first.group or first.lead or (first.slots[0].label if first.slots else "Session")
    session = _make_session(
        meeting_id=meeting_id, day=day, day_date=day_date, room=room, start=start, end=end,
        title=title, group=first.group, lead=first.lead, note=note, source=source,
    )
    session.agendaItems = codes or session.agendaItems
    session.agendaBreakdown = breakdown if len(breakdown) > 1 else []
    return session
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
    if codes:
        label = re.sub(r"^AI\s+", "", label).strip()
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
