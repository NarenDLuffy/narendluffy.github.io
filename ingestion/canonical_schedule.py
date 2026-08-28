"""Build ONE canonical RAN1 schedule out of every parsed schedule document.

Different chairs publish the same week at different levels of detail: the week
grid knows the room and the two-hour block, a sub-chair's own document knows
that the block is really 10.8.3 (40) / 10.8.1 (40) / 10.8.2 (40). Neither
document alone is the schedule; the schedule is the synthesis of all of them.

Pipeline (all documents first, then the day, never one file at a time):

    parsed sessions (every source)
        -> candidate blocks           (containers + atomic children)
        -> per day / per room timeline
        -> duplicates merged, provenance kept
        -> containers split by the detail that is actually evidenced
        -> conflicts flagged, confidence scored
        -> canonical atomic blocks

Rules that must not be broken:

  * detail is only ever taken from a schedule document, never invented from the
    agenda tree (a parent existing does not mean its children are scheduled),
  * a container is never published on top of the detail it was split into,
  * order comes from the detailed source, never from numeric sorting,
  * field level precedence: room / block boundaries from the broad source,
    child items, order and durations from the detailed source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from .models import (
    AgendaSlot,
    ScheduleConflict,
    Session,
    SessionSourceRef,
)

MIN_FRAGMENT_MINUTES = 5


def _mins(hhmm: str) -> int:
    hour, minute = hhmm.split(":")[:2]
    return int(hour) * 60 + int(minute)


def _hhmm(total: int) -> str:
    total = max(0, min(total, 24 * 60 - 1))
    return f"{total // 60:02d}:{total % 60:02d}"


CODE_RE = re.compile(r"^\d{1,2}(?:\.[0-9x]{1,2})*$", re.I)


def _depth(code: str | None) -> int:
    return code.count(".") + 1 if code else 0


def is_descendant(child: str | None, parent: str | None) -> bool:
    """10.8.1 is a descendant of 10.8; 10.8 is not a descendant of itself."""
    if not child or not parent or child == parent:
        return False
    return child.startswith(parent + ".")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:24] or "x"


@dataclass
class CandidateBlock:
    """One time block as a single schedule document describes it."""

    meetingId: str
    date: str
    day: str
    startTime: str
    endTime: str
    roomId: str
    roomName: str
    agendaItems: list[str]
    topic: str
    topicKey: str
    sourceIds: list[str]
    sourceType: str = "unknown"
    kind: str = "session"
    status: str = "scheduled"
    mode: str | None = None
    group: str | None = None
    sessionLead: str | None = None
    note: str | None = None
    label: str | None = None
    parentAgendaItem: str | None = None
    derivation: str = "direct"
    order: int = 0
    affinity: float = 0.0
    origin: Session | None = None

    @property
    def start(self) -> int:
        return _mins(self.startTime)

    @property
    def end(self) -> int:
        return _mins(self.endTime)

    @property
    def minutes(self) -> int:
        return max(0, self.end - self.start)

    @property
    def primary_code(self) -> str | None:
        return self.agendaItems[0] if self.agendaItems else None

    @property
    def specificity(self) -> int:
        """Deepest agenda level this block resolves, 0 when it has no code."""
        return max((_depth(c) for c in self.agendaItems), default=0)

    @property
    def atomic(self) -> bool:
        return len(self.agendaItems) <= 1

    @property
    def confidence(self) -> float:
        base = 0.55
        if self.derivation == "direct":
            base = 0.9
        elif self.derivation == "split-from-parent":
            base = 0.8
        elif self.derivation == "inferred-duration":
            base = 0.7
        if len(self.sourceIds) > 1:
            base = min(0.99, base + 0.05)
        if self.specificity == 0:
            base -= 0.1
        return round(max(0.2, min(base, 0.99)), 2)


# --- candidate extraction ----------------------------------------------------


def _slot_code(slot: AgendaSlot) -> str | None:
    if slot.code and CODE_RE.match(slot.code):
        return slot.code
    return None


def candidates_from_session(session: Session) -> list[CandidateBlock]:
    """A parsed session becomes either a container or its detailed children.

    The children are only produced when the document itself gave a per-item
    time or duration; a bare list of agenda items stays one container block.
    """
    common = dict(
        meetingId=session.meetingId,
        date=session.date,
        day=session.day,
        roomId=session.roomId,
        roomName=session.roomName,
        topic=session.topic,
        topicKey=session.topicKey,
        sourceIds=[ref.sourceId for ref in session.sources],
        kind=session.kind,
        status=session.status,
        mode=session.mode,
        group=session.group,
        sessionLead=session.sessionLead,
        note=session.note,
        origin=session,
    )

    breakdown = [s for s in (session.agendaBreakdown or []) if s.startTime and s.endTime]
    if session.kind in {"session", "plenary"} and breakdown:
        blocks: list[CandidateBlock] = []
        for index, slot in enumerate(breakdown):
            code = _slot_code(slot)
            blocks.append(
                CandidateBlock(
                    startTime=slot.startTime,  # type: ignore[arg-type]
                    endTime=slot.endTime,  # type: ignore[arg-type]
                    agendaItems=[code] if code else [],
                    label=slot.label,
                    parentAgendaItem=_container_code(session.agendaItems, code),
                    derivation="inferred-duration" if slot.minutes else "direct",
                    sourceType="detailed",
                    order=index,
                    **common,  # type: ignore[arg-type]
                )
            )
        return blocks

    return [
        CandidateBlock(
            startTime=session.startTime,
            endTime=session.endTime,
            agendaItems=list(session.agendaItems),
            label=session.topic,
            derivation="direct",
            sourceType="main" if len(session.agendaItems) != 1 else "direct",
            **common,  # type: ignore[arg-type]
        )
    ]


def _container_code(items: Iterable[str], code: str | None) -> str | None:
    if not code:
        return None
    for item in items:
        if is_descendant(code, item):
            return item
    return code.rsplit(".", 1)[0] if "." in code else None


def _score_room_affinity(blocks: list[CandidateBlock]) -> None:
    """How much of each document is about each room.

    A sub-chair's plan spends nearly all of itself on the one room they run, so
    for that room it outranks the week grid, which spreads over every room.
    The same document is *not* promoted for a room it only mentions in passing,
    which keeps one chair's placeholder from overwriting another chair's room.
    """
    per_doc: dict[str, int] = {}
    per_doc_room: dict[tuple[str, str], int] = {}
    for block in blocks:
        for source_id in block.sourceIds:
            per_doc[source_id] = per_doc.get(source_id, 0) + 1
            key = (source_id, block.roomId)
            per_doc_room[key] = per_doc_room.get(key, 0) + 1
    for block in blocks:
        block.affinity = max(
            (
                per_doc_room[(source_id, block.roomId)] / per_doc[source_id]
                for source_id in block.sourceIds
                if per_doc.get(source_id)
            ),
            default=0.0,
        )


# --- canonicalization --------------------------------------------------------


@dataclass
class CanonicalResult:
    sessions: list[Session]
    conflicts: list[ScheduleConflict] = field(default_factory=list)


def canonicalize(sessions: list[Session]) -> CanonicalResult:
    """Collapse every parsed session from every document into one timeline."""
    candidates: list[CandidateBlock] = []
    for session in sessions:
        candidates.extend(candidates_from_session(session))
    _score_room_affinity(candidates)

    conflicts: list[ScheduleConflict] = []
    out: list[Session] = []

    groups: dict[tuple[str, str], list[CandidateBlock]] = {}
    for block in candidates:
        groups.setdefault((block.date, block.roomId), []).append(block)

    for (_date, _room), group in sorted(groups.items()):
        resolved, group_conflicts = _resolve_room_day(group)
        out.extend(_to_session(b) for b in resolved)
        conflicts.extend(group_conflicts)

    out.sort(key=lambda s: (s.date, s.startTime, s.roomName, s.startTime))
    return CanonicalResult(sessions=out, conflicts=conflicts)


def _resolve_room_day(blocks: list[CandidateBlock]) -> tuple[list[CandidateBlock], list[ScheduleConflict]]:
    """One room, one day: merge duplicates, then let detail replace breadth."""
    session_blocks = [b for b in blocks if b.kind in {"session", "plenary"}]
    non_sessions = [b for b in blocks if b.kind not in {"session", "plenary"}]

    session_blocks, conflicts = _merge_duplicates(session_blocks)
    session_blocks.sort(key=lambda b: (b.start, b.end, b.order))

    # Every atomic block that resolves an agenda item is potential detail for
    # a broader block covering the same time in the same room.
    detail = [b for b in session_blocks if b.atomic and b.specificity >= 2]

    kept: list[CandidateBlock] = []
    for block in session_blocks:
        covering = _covering(block, detail)
        if not covering:
            kept.append(block)
            continue
        # The block is a container for finer, evidenced blocks: publish the
        # children, and only whatever time they do not account for.
        kept.extend(_remaining_of(block, detail))

    kept = _drop_overlaps(kept)
    kept.extend(_merge_duplicates(non_sessions)[0])
    kept.sort(key=lambda b: (b.start, b.end, b.order))
    return kept, conflicts



def _drop_overlaps(blocks: list[CandidateBlock]) -> list[CandidateBlock]:
    """Keep one non-overlapping timeline per room/day, finest evidence first.

    Two documents can tile the same afternoon differently (one 60-minute block
    against a 40/40 split). Nesting is handled by the container split above;
    what is left here are partial overlaps, where the more detailed and better
    corroborated block wins and the coarser one is dropped.
    """
    ranked = sorted(
        blocks,
        key=lambda b: (
            -b.specificity,
            b.end - b.start,
            -b.confidence,
            -len(b.sourceIds),
            b.start,
        ),
    )
    kept: list[CandidateBlock] = []
    for block in ranked:
        clash = [o for o in kept if block.start < o.end and o.start < block.end]
        # Identical slots with different agenda items are a reported conflict,
        # not two tilings of the same time - both stay visible.
        if clash and not all(
            o.start == block.start and o.end == block.end for o in clash
        ):
            continue
        kept.append(block)
    kept.sort(key=lambda b: (b.start, b.end, b.order))
    return kept


def _covering(container: CandidateBlock, detailed: list[CandidateBlock]) -> list[CandidateBlock]:
    """Detailed blocks that are evidence about this very container.

    Same room and inside its time range, and either a descendant of one of the
    container's agenda items or - when the container carries the same code -
    the same item. A block about an unrelated agenda item never removes time
    from a container: that is a conflict, not a split.
    """
    inside: list[CandidateBlock] = []
    for block in detailed:
        if block.start < container.start or block.end > container.end:
            continue
        if block is container:
            continue
        code = block.primary_code
        if not container.agendaItems:
            inside.append(block)
            continue
        if any(is_descendant(code, item) or code == item for item in container.agendaItems):
            inside.append(block)
    return inside


def _remaining_of(container: CandidateBlock, detailed: list[CandidateBlock]) -> list[CandidateBlock]:
    """Container time that no detailed block accounts for (may be nothing)."""
    covering = _covering(container, detailed)
    if not covering:
        return [container]

    cursor = container.start
    gaps: list[tuple[int, int]] = []
    for block in sorted(covering, key=lambda b: b.start):
        if block.start > cursor:
            gaps.append((cursor, block.start))
        cursor = max(cursor, block.end)
    if cursor < container.end:
        gaps.append((cursor, container.end))

    fragments: list[CandidateBlock] = []
    for start, end in gaps:
        if end - start < MIN_FRAGMENT_MINUTES:
            continue
        fragment = _clone(container, start, end)
        fragment.derivation = "split-from-parent"
        fragment.note = _join_note(container.note, "Detailed timing not available")
        fragments.append(fragment)
    return fragments


def _clone(block: CandidateBlock, start: int, end: int) -> CandidateBlock:
    data = {**block.__dict__}
    data["startTime"] = _hhmm(start)
    data["endTime"] = _hhmm(end)
    data["agendaItems"] = list(block.agendaItems)
    data["sourceIds"] = list(block.sourceIds)
    return CandidateBlock(**data)


def _join_note(*parts: str | None) -> str | None:
    seen = [p for p in parts if p]
    return " · ".join(dict.fromkeys(seen)) or None


def _identity(block: CandidateBlock) -> tuple:
    return (
        block.date,
        block.roomId,
        block.startTime,
        block.endTime,
        tuple(block.agendaItems),
        block.kind,
    )


def _merge_duplicates(blocks: list[CandidateBlock]) -> tuple[list[CandidateBlock], list[ScheduleConflict]]:
    """One card per real block; all describing documents kept as provenance."""
    merged: dict[tuple, CandidateBlock] = {}
    for block in blocks:
        key = _identity(block)
        current = merged.get(key)
        if current is None:
            merged[key] = block
            continue
        current.sourceIds = list(dict.fromkeys([*current.sourceIds, *block.sourceIds]))
        # A document that covers only this room (a sub-chair's own plan) knows
        # the slot better than the week grid, so its wording wins even when the
        # grid's placeholder is longer.
        closer = block.affinity > current.affinity + 0.05
        if closer or (
            abs(block.affinity - current.affinity) <= 0.05
            and len(block.label or "") > len(current.label or "")
        ):
            current.label = block.label
            current.topic = block.topic
            current.origin = block.origin or current.origin
            current.affinity = max(current.affinity, block.affinity)
        current.note = _join_note(current.note, block.note)
        current.sessionLead = current.sessionLead or block.sessionLead
        current.group = current.group or block.group
        current.mode = current.mode or block.mode
        if len(block.roomName) > len(current.roomName):
            current.roomName = block.roomName

    kept = list(merged.values())
    return kept, _detect_conflicts(kept)


def _detect_conflicts(blocks: list[CandidateBlock]) -> list[ScheduleConflict]:
    """Same room, same slot, incompatible agenda item -> flag, never guess."""
    conflicts: list[ScheduleConflict] = []
    by_slot: dict[tuple, list[CandidateBlock]] = {}
    for block in blocks:
        if block.kind not in {"session", "plenary"} or not block.agendaItems:
            continue
        by_slot.setdefault((block.date, block.roomId, block.startTime, block.endTime), []).append(block)
    for (date, room, start, end), group in by_slot.items():
        if len(group) < 2:
            continue
        codes = {b.primary_code for b in group if b.primary_code}
        if len(codes) < 2:
            continue
        if any(
            is_descendant(a, b) or is_descendant(b, a) for a in codes for b in codes if a != b
        ):
            continue
        conflicts.append(
            ScheduleConflict(
                conflictId=f"conf-{_slug(room)}-{date}-{start}",
                meetingId=group[0].meetingId,
                sessionId=_block_id(group[0]),
                field="agendaItem",
                values=[
                    {
                        "sourceId": ",".join(b.sourceIds) or "unknown",
                        "value": ", ".join(b.agendaItems),
                    }
                    for b in group
                ],
            )
        )
    return conflicts


def _block_id(block: CandidateBlock) -> str:
    code = block.primary_code or _slug(block.topic)
    return "_".join(
        [
            block.meetingId,
            block.day[:3].lower() or block.date,
            _slug(block.roomName),
            block.startTime.replace(":", ""),
            block.endTime.replace(":", ""),
            code,
        ]
    )


def _to_session(block: CandidateBlock) -> Session:
    origin = block.origin
    label = (block.label or block.topic or "").strip()
    topic = origin.topic if origin else label
    slot_label = label if label and label != topic else None

    session = Session(
        sessionId=_block_id(block),
        meetingId=block.meetingId,
        date=block.date,
        day=block.day,
        startTime=block.startTime,
        endTime=block.endTime,
        roomId=block.roomId,
        roomName=block.roomName,
        topic=topic or label or "Session",
        topicKey=block.topicKey,
        agendaItems=list(block.agendaItems),
        agendaBreakdown=[],
        sessionLead=block.sessionLead,
        group=block.group,
        mode=block.mode,
        kind=block.kind,  # type: ignore[arg-type]
        status=block.status,  # type: ignore[arg-type]
        note=block.note,
        sources=[SessionSourceRef(sourceId=sid, contributed=[]) for sid in block.sourceIds],
    )
    # Keep the sub-item wording ("10.8.1 Measurements") without re-introducing
    # a second, overlapping card for it.
    if slot_label and block.agendaItems:
        session.agendaBreakdown = [
            AgendaSlot(
                code=block.primary_code,
                label=slot_label,
                minutes=block.minutes or None,
                startTime=block.startTime,
                endTime=block.endTime,
            )
        ]
    session.derivation = block.derivation  # type: ignore[arg-type]
    session.confidence = block.confidence
    session.parentAgendaItem = block.parentAgendaItem
    session.detailAvailable = block.derivation != "split-from-parent"
    return session
