"""Acceptance tests for canonical schedule generation (spec sections 35-39)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ingestion.canonical_schedule import canonicalize  # noqa: E402
from ingestion.models import AgendaSlot, Session, SessionSourceRef  # noqa: E402


def make(
    start: str,
    end: str,
    *,
    items: list[str],
    breakdown: list[tuple[str, str, str]] | None = None,
    source: str = "src",
    room: str = "himalaya",
    topic: str = "6G ISAC",
) -> Session:
    return Session(
        sessionId=f"{source}-{start}",
        meetingId="ran1-126",
        date="2025-11-18",
        day="Tuesday",
        startTime=start,
        endTime=end,
        roomId=room,
        roomName="1.1 Himalaya",
        topic=topic,
        topicKey="isac",
        agendaItems=items,
        agendaBreakdown=[
            AgendaSlot(code=code, label=code, startTime=s, endTime=e)
            for code, s, e in (breakdown or [])
        ],
        sources=[SessionSourceRef(sourceId=source)],
    )


def test_broad_block_is_replaced_by_detailed_children():
    """Section 35: 10.8 11:00-13:00 + detailed children -> three blocks."""
    broad = make("11:00", "13:00", items=["10.8"], source="main")
    detailed = make(
        "11:00",
        "13:00",
        items=["10.8"],
        breakdown=[("10.8.3", "11:00", "11:40"), ("10.8.1", "11:40", "12:20"), ("10.8.2", "12:20", "13:00")],
        source="hiroki",
    )
    result = canonicalize([broad, detailed])
    got = [(s.startTime, s.endTime, s.agendaItems) for s in result.sessions]
    assert got == [
        ("11:00", "11:40", ["10.8.3"]),
        ("11:40", "12:20", ["10.8.1"]),
        ("12:20", "13:00", ["10.8.2"]),
    ]
    assert all(s.roomName == "1.1 Himalaya" for s in result.sessions)


def test_order_and_repeats_are_preserved():
    """Section 36: keep the discussion order and repeated items."""
    detailed = make(
        "09:00",
        "10:50",
        items=["10.8"],
        breakdown=[("10.8.3", "09:00", "09:30"), ("10.8.1", "09:30", "10:20"), ("10.8.3", "10:20", "10:50")],
        source="hiroki",
    )
    result = canonicalize([detailed])
    assert [s.agendaItems[0] for s in result.sessions] == ["10.8.3", "10.8.1", "10.8.3"]


def test_no_detail_is_invented():
    """Section 37: a lone broad block stays broad."""
    result = canonicalize([make("14:30", "16:30", items=["10.8"], source="main")])
    assert len(result.sessions) == 1
    only = result.sessions[0]
    assert only.agendaItems == ["10.8"]
    assert only.startTime == "14:30" and only.endTime == "16:30"


def test_many_files_give_one_schedule_without_duplicates():
    """Sections 16 + 38: identical blocks from several files merge into one."""
    copies = [make("11:00", "12:00", items=["10.8.2"], source=name) for name in ("a", "b", "c")]
    result = canonicalize(copies)
    assert len(result.sessions) == 1
    assert sorted(ref.sourceId for ref in result.sessions[0].sources) == ["a", "b", "c"]


def test_partial_split_keeps_the_remainder_as_container():
    """Section 20: only detail the part that is evidenced."""
    broad = make("14:30", "16:30", items=["10.8"], source="main")
    detailed = make(
        "14:30",
        "15:50",
        items=["10.8"],
        breakdown=[("10.8.1", "14:30", "15:10"), ("10.8.2", "15:10", "15:50")],
        source="sub",
    )
    result = canonicalize([broad, detailed])
    got = [(s.startTime, s.endTime, s.agendaItems) for s in result.sessions]
    assert got == [
        ("14:30", "15:10", ["10.8.1"]),
        ("15:10", "15:50", ["10.8.2"]),
        ("15:50", "16:30", ["10.8"]),
    ]
    remainder = result.sessions[-1]
    assert remainder.detailAvailable is False
    assert "Detailed timing not available" in (remainder.note or "")


def test_unrelated_agenda_item_is_a_conflict_not_a_split():
    """Section 32: contradicting sources are flagged, never silently picked."""
    a = make("14:30", "15:30", items=["10.8.2"], source="a")
    b = make("14:30", "15:30", items=["10.9.1"], source="b")
    result = canonicalize([a, b])
    assert len(result.conflicts) == 1
    assert len(result.sessions) == 2
