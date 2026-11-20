from ingestion.block_schedule import _parse_cell, _sessions_for_cell
from ingestion.models import Room, ScheduleSource


def _slots(text):
    return [[(s.label, s.minutes) for s in g.slots] for g in _parse_cell(text)]


def test_child_fills_its_parent_item():
    # Hiroki RAN1#127 Thursday: 10.8 Sensing (50) is 10.8.3 for those 50 minutes.
    out = _slots("6GR (110)\n.10.8 Sensing (50)\n 10.8.3 (50)\n\n.10.5.4.1 (60)")
    assert out[0] == [("10.8.3", 50), ("10.5.4.1", 60)]


def test_named_item_takes_its_code():
    out = _slots("R20 (60)\nA-IoT Phase2 (60)\n 9.3.3 (60)")
    assert out == [[("9.3.3", 60)]]


def test_children_that_do_not_fill_parent_are_left_alone():
    out = _slots("6GR (120)\n.10.5.1 Waveform (30)\n.10.8 Sensing (90)\n10.8.1 (30)\n10.8.2 (30)")
    assert ("10.8 Sensing", 90) in out[0]


def test_untimed_items_under_timed_head_keep_their_codes():
    # Hiroki RAN1#127 hh4 Thursday, BMO 214-215: no minutes, so no split, but all items listed.
    groups = _parse_cell("TEI, AI 7/8.1 (40)\n7 pre-Rel-19 CRs\n8.1 Duplex\n8.1 Mobility\n11 TEI20")
    assert [c for s in groups[0].slots for c in s.codes] == ["7", "8.1", "8.1", "11"]


def test_code_lines_after_short_head_are_their_own_blocks():
    # Sorour RAN1#127 v04 Friday Room 225-226.
    groups = _parse_cell("[TBD\xa0: AI/ML,MIMO]? (20)\n9.5 NTN (30)\n10.7.1 NTN (30)\n9.4 NR-NTN (40)\n.10.5.2.2 (30)")
    assert [g.minutes for g in groups][:4] == [20, 30, 30, 40]


def test_shared_code_list_does_not_collapse_hiroki_hh7_friday_cell():
    # Exact hh7 Friday BMO 214-215 cell: 30 + 50 + 10 + 60 = 150 minutes.
    text = "8.1 ISAC (30)\n\n6GR (50)\n.10.8 Sensing (50)\n10.8.1 (30)\n10.8.2 (20)\n\n10.5.4.x post-meeting email discussion (10)\n\nR20 (60)\nA-IoT Phase2 (60)\n9.3.1, 9.3.2, [9.3.3], LS/TP (60)"
    room = Room(roomId="r", meetingId="ran1-127", roomName="BMO 214-215", order=0)
    source = ScheduleSource(
        sourceId="hh7", meetingId="ran1-127", fileName="hh7.docx", label="hh7",
        type="offline_schedule", origin="public", retrievedAt="now",
    )
    sessions = _sessions_for_cell(
        text, meeting_id="ran1-127", day="Friday", day_date="2026-11-20",
        room=room, block_start=8 * 60, block_end=10 * 60 + 30, source=source,
    )
    assert [(s.startTime, s.endTime, s.agendaItems) for s in sessions] == [
        ("08:00", "08:30", ["8.1"]),
        ("08:30", "09:00", ["10.8.1"]),
        ("09:00", "09:20", ["10.8.2"]),
        ("09:20", "09:30", ["10.5.4.x"]),
        ("09:30", "10:30", ["9.3.1", "9.3.2", "9.3.3"]),
    ]
    assert all("Minutes don't add up" not in (s.note or "") for s in sessions)
