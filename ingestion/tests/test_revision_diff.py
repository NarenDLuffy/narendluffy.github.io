"""Latest-change rule: a fresh edit beats untouched copies in other files."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ingestion.canonical_schedule import canonicalize  # noqa: E402
from ingestion.models import Session, SessionSourceRef  # noqa: E402
from ingestion.revision_diff import mark_edits, record_revision  # noqa: E402


def make(items, source="s", start="12:30", end="13:00", room="room-201"):
    return Session(sessionId=f"{source}-{start}-{items}", meetingId="m", date="2026-10-15", day="Thursday",
                   startTime=start, endTime=end, roomId=room, roomName="Room 201", topic="x",
                   topicKey="default", agendaItems=list(items), sources=[SessionSourceRef(sourceId=source)])


def family(h, name, revisions):
    """revisions oldest first: (file, time, sessions). Marks and returns the latest sessions."""
    for file, at, sessions in revisions:
        record_revision(h, name, file, at, sessions)
    latest = revisions[-1]
    older = [r[0] for r in reversed(revisions[:-1])]
    return mark_edits(h, name, latest[0], older, latest[2]), latest[2]


def test_edited_main_beats_two_stale_copies():
    """RAN1#126bis Thu Room 201 12:30: main edits to 10.5.3.4, two copies keep 10.5.3.2."""
    h: dict = {}
    _, main = family(h, "main", [("v02", "T1", [make(["10.5.3.2"])]), ("v03", "T3", [make(["10.5.3.4"], "main")]),
                                 ("v04", "T4", [make(["10.5.3.4"], "main")])])
    _, sorour = family(h, "sorour", [("v00", "T1", [make(["10.5.3.2"])]), ("v01", "T4", [make(["10.5.3.2"], "sorour")])])
    _, hiroki = family(h, "hiroki", [("v05", "T2", [make(["10.5.3.2"])]), ("v06", "T5", [make(["10.5.3.2"], "hiroki")])])
    result = canonicalize([*sorour, *hiroki, *main])
    assert [s.agendaItems for s in result.sessions] == [["10.5.3.4"]]
    assert "older copy" in (result.sessions[0].note or "")


def test_first_release_falls_back_to_votes():
    h: dict = {}
    blocks = []
    for name, items in (("a", ["10.5.3.4"]), ("b", ["10.5.3.2"]), ("c", ["10.5.3.2"])):
        blocks += family(h, name, [("v00", "T1", [make(items, name)])])[1]
    assert canonicalize(blocks).sessions[0].agendaItems == ["10.5.3.2"]


def test_formatting_only_change_is_not_an_edit():
    h: dict = {}
    n, _ = family(h, "f", [("v1", "T1", [make(["10.5.3.x"])]), ("v2", "T2", [make(["10.5.3.X"])])])
    assert n == 0


def test_inserted_block_does_not_mark_others_edited():
    h: dict = {}
    prev = [make(["9.1"], start="09:00", end="10:00"), make(["9.2"], start="10:00", end="11:00")]
    latest = [make(["9.1"], start="09:00", end="10:00"), make(["8.1"], start="11:00", end="11:30"),
              make(["9.2"], start="10:00", end="11:00")]
    n, _ = family(h, "f", [("v1", "T1", prev), ("v2", "T2", latest)])
    assert n == 1


def test_edited_grid_beats_unchanged_detail_in_same_file():
    """Friday v04: the grid moved 10.5.1.3 first; the detail table kept v03's order."""
    h: dict = {}
    _, grid = family(h, "grid", [("v03", "T3", [make(["10.5.1.1"], start="08:30", end="09:00")]),
                                 ("v04", "T4", [make(["10.5.1.3"], "v04", "08:30", "09:00")])])
    _, detail = family(h, "detail", [("v03", "T3", [make(["10.5.1.1"], start="08:30", end="09:00")]),
                                     ("v04", "T4", [make(["10.5.1.1"], "v04", "08:30", "09:00")])])
    detail[0].sources.append(SessionSourceRef(sourceId="sorour"))
    assert canonicalize([*detail, *grid]).sessions[0].agendaItems == ["10.5.1.3"]
