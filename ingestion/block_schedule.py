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
from dataclasses import dataclass, field
from datetime import date, timedelta

from docx import Document

from .docx_active_text import active_paragraph_text
from .canonical_schedule import is_descendant
from .models import AgendaSlot, Room, ScheduleSource, Session, SessionSourceRef

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

TIME_RE = re.compile(r"(\d{1,2})[:.](\d{2})")
BLOCK_RE = re.compile(r"(\d{1,2})[:.](\d{2})\s*(?:~|-|–|to)\s*(\d{1,2})[:.](\d{2})")
BREAK_RE = re.compile(r"\b(break|lunch|coffee)\b", re.I)
DURATION_RE = re.compile(r"\(\s*~?\s*(\d{1,3})\s*(?:min|mins|minutes)?\s*\)\s*$", re.I)
# "Maintenance (90-120)": a head whose length is a range. Its items' own
# stated minutes decide the block when their sum falls inside the range.
RANGE_DURATION_RE = re.compile(r"\(\s*(\d{1,3})\s*[-–~]\s*(\d{1,3})\s*(?:min|mins|minutes)?\s*\)\s*$", re.I)
# "7 pre-Rel-19 CRs (50)" / "11 TEI20 (10)": a top-level agenda number opening
# a timed item line under a head. Only read in that position, never in prose.
LEADING_CODE_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2})*)\s+(?=[A-Za-z])")
LISTED_CODE_RE = re.compile(r"(?:^|[,;]\s*)(\d{1,2}(?:\.\d{1,2})*)\s+(?=[A-Za-z])")
TBD_RE = re.compile(r"\(\s*(tbd|n/?a)\s*\)\s*$", re.I)
AGENDA_CODE_RE = re.compile(r"\b(\d{1,2}(?:\.(?:\d{1,2}|x))+)", re.I)
MAIN_FILE_RE = re.compile(r"^\s*(?:draft\s+)?RAN1\s*#\s*\w+\s+online\s+and\s+offline\s+schedules?\s*-\s*v\d+\s*$", re.I)
GENERIC_GRID_RE = re.compile(r"\bRAN1\s*#\s*\w+\s+(?:online|offline)(?:\s+and\s+offline)?\s+sessions?\s+schedules?\b", re.I)
STARTS_AT_RE = re.compile(r"\bat\s+(\d{1,2})[:.](\d{2})", re.I)

# Short work-area labels chairs use as a group tag rather than a person.
GROUP_TOKENS = {
    "6gr", "6g", "r20", "r19", "r18", "nr", "lte", "tei", "ai", "ai/ml", "aiml",
    "ntn", "ntn-nr", "ntn-iot", "a-iot", "isac", "mimo", "sweep", "plenary",
    "maintenance", "tbd", "dinner",
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
    # "Detailed Schedule for RAN1 Brk#2 Session (BMO 214-215)": a trailing
    # bracket after a session label names the room.
    tail = re.search(r"\(\s*([^()]+?)\s*\)\s*$", heading or "")
    if tail and _SESSION_LABEL_RE.search(heading[: tail.start()]):
        name = tail.group(1).strip(" -–—:·")
        if (re.search(r"[A-Za-z]", name) and not _SESSION_LABEL_RE.search(name)
                and not re.fullmatch(r"\d{1,2}\s*F", name, re.I)
                and not re.search(r"\b(mon|tue|wed|thu|fri)", name, re.I)):
            return name
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
    codes: list[str] = field(default_factory=list)


@dataclass
class _Segment:
    lead: str | None
    group: str
    minutes: int | None
    slots: list[_Slot]
    raw: str
    # Lower bound of a ranged head ("(90-120)"); minutes holds the upper bound.
    min_minutes: int | None = None


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



def _item_codes(label: str) -> list[str]:
    """Every agenda item a timed item line names, in order ("7 …, 8.2 …" → 7, 8.2)."""
    found: list[tuple[int, str]] = [(m.start(1), m.group(1)) for m in LISTED_CODE_RE.finditer(label)]
    found += [(m.start(1), m.group(1)) for m in AGENDA_CODE_RE.finditer(label)]
    out: list[str] = []
    for _, code in sorted(found):
        if code not in out:
            out.append(code)
    return out


def _items_minutes_after(lines: list[str], index: int) -> int:
    """Stated minutes of the item lines that directly follow lines[index]."""
    total = 0
    for line in lines[index + 1:]:
        codes = _code_list(line)
        label, minutes = _split_head(line)
        if codes:
            total += sum(m or 0 for _, m in codes)
        elif line.startswith(".") or LEADING_CODE_RE.match(label):
            total += minutes or 0
        else:
            break
    return total


def _nested_in_previous(slots: list["_Slot"], label: str, minutes: int | None) -> bool:
    """True when a timed item details the timed item just before it.

    ".10.8 Sensing (50) / 10.8.3 (50) / .10.5.4.1 (60)" under "6GR (110)":
    10.8.3 is the content of the 50 Sensing minutes, not 50 more minutes.
    """
    if not minutes or not slots:
        return False
    codes = AGENDA_CODE_RE.findall(label)
    if not codes:
        return False
    used = 0
    for slot in reversed(slots):
        slot_codes = AGENDA_CODE_RE.findall(slot.label)
        if not slot_codes:
            return False
        if is_descendant(codes[0], slot_codes[0]) and slot_codes[0] != codes[0]:
            return bool(slot.minutes) and used + minutes <= slot.minutes
        if not is_descendant(slot_codes[0], codes[0].rsplit(".", 1)[0]):
            return False
        used += slot.minutes or 0
    return False


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
    after_blank: set[int] = set()
    # "|" closes the open head: ".9.5 NTN (20) | 6GR (90)" — what follows is a
    # new block, never an item of the previous head.
    hard_break: set[int] = set()
    pieces: list[str] = []
    for raw_line in text.split("\n"):
        parts = raw_line.split("|")
        for n, part in enumerate(parts):
            if n:
                pieces.append("\x00")
            pieces.append(part)
    for raw_line in pieces:
        if raw_line == "\x00":
            if lines:
                hard_break.add(len(lines))
            continue
        stripped = raw_line.strip()
        if not stripped:
            if lines:
                after_blank.add(len(lines))
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
        if current.slots and not any(slot.minutes for slot in current.slots):
            # "R20 A-IoT (60)" / "9.3.1": the untimed item list completes it.
            return True
        if current.min_minutes is not None and allocated >= current.min_minutes:
            return True
        return allocated >= current.minutes

    def tag_finished() -> bool:
        if current is None:
            return True
        if current.minutes is None:
            return bool(current.slots)
        return allocated >= current.minutes

    for line_index, line in enumerate(lines):
        if line_index in hard_break:
            current, current_group, allocated = None, "", 0
        codes = _code_list(line)
        # "A-IoT Phase2 (60) / 9.3.3 (60)": the code list is the agenda item of
        # the named item just above it, filling exactly its minutes.
        names_previous = bool(
            codes and current is not None and current.slots
            and not AGENDA_CODE_RE.findall(current.slots[-1].label)
            and current.slots[-1].minutes
            and all(m for _, m in codes)
            and sum(m or 0 for _, m in codes) == current.slots[-1].minutes
        )
        if (
            codes
            and not names_previous
            and current is not None
            and current.minutes
            and allocated >= current.minutes
            and all(m for _, m in codes)
            and not (
                current.slots
                and (first_codes := AGENDA_CODE_RE.findall(current.slots[0].label))
                and all(is_descendant(code, first_codes[0]) for code, _ in codes)
            )
        ):
            # Timed items after the head's minutes are used up: next block.
            current = _Segment(lead=None, group=current_group or current.group, minutes=None, slots=[], raw="")
            segments.append(current)
            allocated = 0
        if codes and current is not None:
            # "9.3.3, 9.3.1, 9.3.2" under a head is the ordered list of agenda
            # items sharing that head's time, not a work-area tag.
            if names_previous:
                current.slots[-1].minutes = -current.slots[-1].minutes  # marks a named container
            for code, code_minutes in codes:
                current.raw += "\n" + code
                nested = names_previous or _nested_in_previous(current.slots, code, code_minutes)
                current.slots.append(
                    _Slot(label=code, minutes=code_minutes, group=current_group or current.group)
                )
                if code_minutes and not nested:
                    allocated += code_minutes
            continue

        ranged = RANGE_DURATION_RE.search(line.rstrip(" ."))
        if ranged and not line.startswith("."):
            label = line.rstrip(" .")[: ranged.start()].strip(" .·-")
            lo, hi = sorted((int(ranged.group(1)), int(ranged.group(2))))
            current = _Segment(lead=None, group=label, minutes=hi, slots=[], raw=line, min_minutes=lo)
            segments.append(current)
            current_group, allocated = label, 0
            continue

        label, minutes = _split_head(line)
        if not label:
            continue
        leading_code = (
            minutes is not None and current is not None and current.minutes is not None
            and not finished() and LEADING_CODE_RE.match(label)
            # "[TBD] (20) / 9.5 NTN (30)": an item longer than what is left
            # of the head is the next block, not part of that head.
            and allocated + minutes <= current.minutes
        )
        is_item = line.startswith(".") or bool(leading_code)

        # "Sorour (90) / 6GR (90) / .10.5.4.1 (40) …": a timed work-area tag
        # inside an open head is a sub-head naming the items below it, not a
        # 90-minute item of its own — but only when those items' stated
        # minutes fit inside it.
        if (
            not is_item and minutes and _is_group_token(label)
            and current is not None and current.minutes is not None
            and not finished() and allocated + minutes <= current.minutes
        ):
            following = _items_minutes_after(lines, line_index)
            # "R20 (60) / NTN-NR (40) / .9.5 (20)": the tag and the items
            # together fill the head, so the tag is an item of its own.
            fits_as_item = following < minutes and allocated + minutes + following <= current.minutes
            if 0 < following <= minutes and not fits_as_item:
                current_group = label
                current.raw += "\n" + line
                continue
        # Any timed, non-item line ("R20 A-IoT (40)", "Maintenance (80)") opens
        # a new block once the previous one has used up its minutes.
        heads_new = not is_item and (
            _looks_like_person(label) or _is_group_token(label) or minutes is not None
        )

        if (
            not is_item and minutes is None and current is not None
            and current.minutes and LEADING_CODE_RE.match(label)
            and not any(slot.minutes for slot in current.slots)
        ):
            # "TEI, AI 7/8.1 (40) / 7 pre-Rel-19 CRs / 8.1 Duplex / 11 TEI20":
            # the untimed agenda items sharing that head's time, in order.
            current.raw += "\n" + line
            current.slots.append(_Slot(
                label=label, minutes=None, group=current_group or current.group,
                codes=_item_codes(label),
            ))
            continue
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


        # "TEI20 (10)", blank line, "Maintenance (70)": a timed head that had no
        # items of its own is complete; the next timed head starts a new block.
        head_after_blank = (
            line_index in after_blank
            and not is_item
            and minutes is not None
            and current is not None
            and current.minutes is not None
            and not current.slots
        )
        new_work_area = (
            not is_item and minutes is not None and current is not None
            and current.minutes is not None and bool(current.slots)
            and _is_group_token(label) and _is_group_token(current.group)
            and label.strip().lower() != current.group.strip().lower()
            # A name-only item such as "NTN-NR (40)" still belongs to the open
            # R20 head when its minutes fit; a new R20 head after 6GR's items
            # cannot fit there and therefore starts its own section.
            and allocated + minutes > current.minutes
        )
        code_overflow = (
            not is_item and minutes is not None and current is not None
            and current.minutes is not None and bool(LEADING_CODE_RE.match(label))
            and allocated + minutes > current.minutes
        )
        if current is None or new_work_area or (heads_new and finished()) or head_after_blank or code_overflow:
            # "6GR (90)" can contain only 80 minutes of items before "R20 (70)".
            # R20 is still a new work area; the earlier head's typo must not
            # swallow it or detach its items into overlapping blocks.
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
            # "9.5 NTN (30)" as a head is itself the item filling its minutes.
            allocated = minutes if (minutes and LEADING_CODE_RE.match(label)) else 0
            continue

        parent_codes = AGENDA_CODE_RE.findall(current.slots[0].label) if current and current.slots else []
        is_child_of_parent = bool(parent_codes) and any(
            is_descendant(code, parent_codes[0]) for code in AGENDA_CODE_RE.findall(label)
        )
        if (
            is_item and minutes and current.minutes and allocated >= current.minutes
            and not is_child_of_parent
        ):
            # A timed item after the head's minutes are used up is the next
            # block of the same work area ("6GR (60) / .10.6.x (60) / .10.5.1.1 (60)").
            current = _Segment(lead=None, group=current_group or current.group, minutes=None, slots=[], raw=line)
            segments.append(current)
            allocated = 0
        current.raw += "\n" + line
        nested = _nested_in_previous(current.slots, label, minutes)
        current.slots.append(_Slot(
            label=label, minutes=minutes, group=current_group or current.group,
            codes=_item_codes(label) if leading_code else [],
        ))

        if minutes and not nested:
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
            and is_descendant(codes[0], parent)
            for child in children
        ):
            segment.slots = children
            if segment.minutes is None or segment.minutes == first.minutes:
                segment.minutes = first.minutes

    for segment in segments:
        _expand_nested_slots(segment)

    return segments


def _expand_nested_slots(segment: "_Segment") -> None:
    """Replace a timed item by its timed children when they fill it exactly.

    "6GR (110) / .10.8 Sensing (50) / 10.8.3 (50) / .10.5.4.1 (60)" becomes
    10.8.3 (50) then 10.5.4.1 (60). Children that do not add up to the parent's
    minutes are left alone, so no time is invented.
    """
    slots = segment.slots
    out: list[_Slot] = []
    i = 0
    while i < len(slots):
        slot = slots[i]
        if slot.minutes is not None and slot.minutes < 0:
            # Named container ("A-IoT Phase2 (60)") whose code list follows.
            j, minutes = i + 1, -slot.minutes
            while j < len(slots) and AGENDA_CODE_RE.findall(slots[j].label) and minutes > 0:
                minutes -= slots[j].minutes or 0
                slots[j].group = slots[j].group or slot.group
                j += 1
            out.extend(slots[i + 1:j])
            i = j
            continue
        codes = AGENDA_CODE_RE.findall(slot.label)
        if codes and slot.minutes:
            j, total = i + 1, 0
            while j < len(slots):
                child_codes = AGENDA_CODE_RE.findall(slots[j].label)
                if not (child_codes and slots[j].minutes and child_codes[0] != codes[0]
                        and is_descendant(child_codes[0], codes[0])):
                    break
                total += slots[j].minutes or 0
                j += 1
            if j > i + 1 and total == slot.minutes:
                out.extend(slots[i + 1:j])
                i = j
                continue
        out.append(slot)
        i += 1
    segment.slots = out



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
        single_lane = all(end - start <= 1 for start, end in days.values())
        # A one-room table is a chair's detail plan. A multi-lane table is the
        # shared week grid even when floating room labels make its heading long;
        # the heading only disambiguates a one-lane shared grid.
        own_table = single_lane and not GENERIC_GRID_RE.search(heading or "")

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
                            sources=[SessionSourceRef(
                                source.sourceId,
                                ["break", *(["own-table"] if own_table else [])],
                            )],
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
                    if cell.continued and cells[0].continued:
                        # Same time block as the row above (e.g. an "Early
                        # dinner" sub-row under 17:00 ~ 19:30): this cell was
                        # already read there. Word often drops the lane colour
                        # on continuation cells, so reading it again would put
                        # another room's items into the white (Main) room.
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
                    cell_ref = "|".join(
                        (
                            source.sourceId,
                            f"t{child.getparent().index(child)}",
                            day,
                            str(block_start),
                            f"c{cell.col_start}",
                            hashlib.sha1(cell.text.strip().encode()).hexdigest()[:8],
                        )
                    )
                    for item in produced:
                        for ref in item.sources:
                            ref.cell = cell_ref
                    if own_table:
                        for item in produced:
                            for ref in item.sources:
                                ref.contributed = [*ref.contributed, "own-table"]
                    sessions.extend(produced)

    sessions = [s for s in sessions if s.startTime < s.endTime]
    # The main chair's shared online/offline grid (no other chair's name or
    # initials in the file name) owns every room's outer times and all breaks.
    # Its one-room detail tables, like every other chair file, add detail only.
    if MAIN_FILE_RE.match(re.sub(r"\.docx$", "", source.fileName or "", flags=re.I)):
        for item in [*sessions, *breaks.values()]:
            for ref in item.sources:
                if "own-table" not in ref.contributed and "main-authority" not in ref.contributed:
                    ref.contributed = [*ref.contributed, "main-authority"]
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
        if seg.min_minutes is not None:
            stated = [slot.minutes for slot in seg.slots]
            if stated and all(stated) and seg.min_minutes <= sum(stated) <= (seg.minutes or 0):
                return sum(stated)  # type: ignore[arg-type]
            return None
        if seg.minutes:
            return seg.minutes
        minutes = [slot.minutes for slot in seg.slots]
        if minutes and all(minutes):
            return sum(m or 0 for m in minutes)
        return None

    lengths = [seg_length(seg) for seg in segments]
    item_lengths: list[int | None] = [
        sum(slot.minutes or 0 for slot in seg.slots)
        if seg.slots and all(slot.minutes for slot in seg.slots)
        # ".10.7.1 NTN (40)" heading a cell is its own timed item.
        else (seg.minutes if not seg.slots and seg.group and LEADING_CODE_RE.match(seg.group) else None)
        for seg in segments
    ]
    if (
        len(segments) > 1
        and sum(length or 0 for length in lengths) > total
        and all(length is not None for length in item_lengths)
        and sum(length or 0 for length in item_lengths) == total
    ):
        # Group headings can be misstated ("6GR (90)" above 40+40 minutes,
        # then "R20 (70)" above 30+40). The item minutes are also explicitly
        # stated and tile the cell exactly, so they govern; no time is invented.
        lengths = item_lengths
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
            first_line = segment.raw.split("\n")[0]
            title = (
                first_line
                if re.search(r"commences|closing|close", first_line, re.I)
                else segment.group or segment.lead or first_line
            )
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
        if len(segment.slots) > 1 and all(stated) and sum(m or 0 for m in stated) == span:
            # Every item has stated minutes and they fill the block exactly: back
            # to back. Minutes that fall short ("Waveform (30)", "Sensing (6)" in a
            # 90-minute block) are a typo, not a schedule — never place them.
            slot_cursor = seg_start
            for slot in segment.slots:
                slot_end = slot_cursor + (slot.minutes or 0)
                out.append(
                    _make_session(
                        start=slot_cursor, end=slot_end, title=slot.label,
                        group=slot.group or segment.group, lead=segment.lead, note=None,
                        codes=slot.codes or None, **common,
                    )
                )
                slot_cursor = slot_end
            continue
        if len(segment.slots) == 1:
            slot = segment.slots[0]
            out.append(
                _make_session(
                    start=seg_start, end=seg_end, title=slot.label,
                    group=slot.group or segment.group, lead=segment.lead, note=None,
                    codes=slot.codes or None, **common,
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
            slot_codes = slot.codes or AGENDA_CODE_RE.findall(slot.label)
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
    codes: list[str] | None = None,
) -> Session:
    clean = re.sub(r"\s+", " ", title).strip(" .·-") or group or "Session"
    if codes:
        label = LISTED_CODE_RE.sub(lambda m: m.group(0)[: m.start(1) - m.start(0)], clean)
        label = AGENDA_CODE_RE.sub("", label)
        label = re.sub(r"\s*,\s*,", ",", re.sub(r"\s+", " ", label)).strip(" .,·-/")
    else:
        codes = AGENDA_CODE_RE.findall(clean)
        label = AGENDA_CODE_RE.sub("", clean).strip(" .·-/") if codes else clean
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
