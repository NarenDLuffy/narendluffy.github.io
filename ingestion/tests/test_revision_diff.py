"""Latest-change rule: a fresh edit beats untouched copies in other files."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ingestion.canonical_schedule import canonicalize  # noqa: E402
from ingestion.models import Session, SessionSourceRef  # noqa: E402
from ingestion.revision_diff import mark_edits  # noqa: E402


def make(items, source, start="12:30", end="13:00", date="2026-10-15", room="room-201"):
    return Session(sessionId=f"{source}-{start}-{items}", meetingId="m", date=date, day="Thursday",
                   startTime=start, endTime=end, roomId=room, roomName="Room 201", topic="x",
                   topicKey="default", agendaItems=list(items), sources=[SessionSourceRef(sourceId=source)])


def test_edited_main_beats_two_stale_copies():
    """RAN1#126bis Thu Room 201 12:30: main v04 says 10.5.3.4, two copies keep 10.5.3.2."""
    h: dict = {}
    main = make(["10.5.3.4"], "main-v04")
    mark_edits("main", [main], [make(["10.5.3.2"], "main-v03")], h, "T2")
    sorour = make(["10.5.3.2"], "sorour-v01")
    mark_edits("sorour", [sorour], [make(["10.5.3.2"], "sorour-v00")], h, "T2")
    hiroki = make(["10.5.3.2"], "hiroki-v06")
    mark_edits("hiroki", [hiroki], [make(["10.5.3.2"], "hiroki-v05")], h, "T2")
    result = canonicalize([sorour, hiroki, main])
    assert [s.agendaItems for s in result.sessions] == [["10.5.3.4"]]
    assert "older copy" in (result.sessions[0].note or "")


def test_first_release_falls_back_to_votes():
    h: dict = {}
    a, b, c = make(["10.5.3.4"], "a"), make(["10.5.3.2"], "b"), make(["10.5.3.2"], "c")
    for fam, s in (("a", a), ("b", b), ("c", c)):
        mark_edits(fam, [s], None, h, "T1")
    assert canonicalize([a, b, c]).sessions[0].agendaItems == ["10.5.3.2"]


def test_edit_remembered_when_next_revision_leaves_it():
    h: dict = {}
    mark_edits("main", [make(["10.5.3.4"], "v05")], [make(["10.5.3.2"], "v04")], h, "T5")
    main = make(["10.5.3.4"], "v06")
    mark_edits("main", [main], [make(["10.5.3.4"], "v05")], h, "T6")
    stale = [make(["10.5.3.2"], "s1"), make(["10.5.3.2"], "s2")]
    for i, s in enumerate(stale):
        mark_edits(f"s{i}", [s], [make(["10.5.3.2"], f"s{i}-old")], h, "T6")
    assert canonicalize([*stale, main]).sessions[0].agendaItems == ["10.5.3.4"]


def test_formatting_only_change_is_not_an_edit():
    h: dict = {}
    n = mark_edits("f", [make(["10.5.3.X"], "v2")], [make(["10.5.3.x"], "v1")], h, "T")
    assert n == 0


def test_inserted_block_does_not_mark_others_edited():
    h: dict = {}
    prev = [make(["9.1"], "v1", "09:00", "10:00"), make(["9.2"], "v1", "10:00", "11:00")]
    latest = [make(["9.1"], "v2", "09:00", "10:00"), make(["8.1"], "v2", "11:00", "11:30"),
              make(["9.2"], "v2", "10:00", "11:00")]
    assert mark_edits("f", latest, prev, h, "T") == 1


def test_edited_grid_beats_unchanged_detail_in_same_file():
    """Friday v04: the grid moved 10.5.1.3 first; the detail table kept v03's order."""
    h: dict = {}
    grid = make(["10.5.1.3"], "v04", "08:30", "09:00")
    detail = make(["10.5.1.1"], "v04", "08:30", "09:00", room="room-201")
    mark_edits("grid", [grid], [make(["10.5.1.1"], "v03", "08:30", "09:00")], h, "T4")
    mark_edits("detail", [detail], [make(["10.5.1.1"], "v03", "08:30", "09:00")], h, "T4")
    detail.sources.append(SessionSourceRef(sourceId="sorour"))
    assert canonicalize([detail, grid]).sessions[0].agendaItems == ["10.5.1.3"]
