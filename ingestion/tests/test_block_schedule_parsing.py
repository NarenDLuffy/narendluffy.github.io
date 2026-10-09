from ingestion.block_schedule import _parse_cell


def test_timed_parent_is_container_for_explicit_timed_children():
    segments = _parse_cell(
        "6GR (120)\n.10.5.4 (120)\n\n"
        ".10.5.4.1 (50)\n.10.5.4.2 (25)\n.10.5.4.3 (40)\n.10.5.4.4 (35)"
    )
    assert len(segments) == 1
    assert [slot.label for slot in segments[0].slots] == [
        "10.5.4.1",
        "10.5.4.2",
        "10.5.4.3",
        "10.5.4.4",
    ]
    assert [slot.minutes for slot in segments[0].slots] == [50, 25, 40, 35]

from ingestion.block_schedule import _sessions_for_cell, norm_room, _heading_room_name
from ingestion.models import Room, ScheduleSource

_ROOM = Room(roomId="r", meetingId="m", roomName="Room", order=0)
_SRC = ScheduleSource(sourceId="s", meetingId="m", fileName="f", label="f", type="x", origin="public", retrievedAt="x")


def _cell(text, start=510, end=630):
    return _sessions_for_cell(
        text, meeting_id="m", day="Tuesday", day_date="2026-10-13", room=_ROOM,
        block_start=start, block_end=end, source=_SRC,
    )


def test_minutes_that_do_not_fit_stay_one_block_with_a_note():
    out = _cell("6GR (120)\n.10.5.4 (120)\n\n.10.5.4.1 (50)\n.10.5.4.2 (25)\n.10.5.4.3 (40)\n.10.5.4.4 (35)")
    assert len(out) == 1
    block = out[0]
    assert (block.startTime, block.endTime) == ("08:30", "10:30")
    assert block.agendaItems[-4:] == ["10.5.4.1", "10.5.4.2", "10.5.4.3", "10.5.4.4"]
    assert [b.minutes for b in block.agendaBreakdown] == [50, 25, 40, 35]
    assert all(not b.startTime for b in block.agendaBreakdown)
    assert "Minutes don't add up: items total 150 min, block is 120 min." in block.note


def test_items_without_minutes_are_never_given_made_up_times():
    out = _cell("6G 10.5.4.x(90)\n10.5.4.1, 10.5.4.3, 10.5.4.4", 900, 990)
    assert len(out) == 1
    assert (out[0].startTime, out[0].endTime) == ("15:00", "16:30")
    assert {"10.5.4.1", "10.5.4.3", "10.5.4.4"} <= set(out[0].agendaItems)


def test_stated_minutes_that_fit_are_split_back_to_back():
    out = _cell("6G ISAC (120)\n10.8.2(40), 10.8.3(40), 10.8.1(40)", 660, 780)
    assert [(s.startTime, s.endTime, s.agendaItems) for s in out] == [
        ("11:00", "11:40", ["10.8.2"]),
        ("11:40", "12:20", ["10.8.3"]),
        ("12:20", "13:00", ["10.8.1"]),
    ]


def test_explicit_time_ranges_inside_a_cell_are_used():
    out = _cell("8:30 - 10:00\n6G ISAC (90)\n10.8.3, 10.8.1\n\n10:00 - 10:30\n6G waveform (30)\n10.2.1")
    assert [(s.startTime, s.endTime) for s in out] == [("08:30", "10:00"), ("10:00", "10:30")]


def test_room_names_match_across_files():
    assert norm_room("Room 201 (2F)") == norm_room("201")
    assert norm_room("Yeongju B (1F)") == norm_room("Yeongju B, 1F")
    assert _heading_room_name("RAN1#126bis X’s Online Session Schedule (room: RAN1_Brk#2, Yeongju B, 1F)") == "Yeongju B"
    assert _heading_room_name("RAN1#126b Detailed Schedule for X’s RAN1 Session @Yeongju A (1F)") == "Yeongju A (1F)"
