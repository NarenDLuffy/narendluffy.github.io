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


def test_minutes_that_fall_short_are_never_placed():
    # Hiroki v03/v05, Wednesday 08:30-10:30 Room 201: the grid copy says
    # "Sensing (6)" (a typo for 60) inside a 90-minute block.
    out = _cell(
        "Xiaodong (30)\n6GR\n.10.5.5 (30)\n\nHiroki (90)\n6GR\n.10.2.1 Waveform(30)\n.10.8.x Sensing (6)"
    )
    times = [(s.startTime, s.endTime) for s in out]
    assert ("08:30", "09:00") in times
    assert ("09:00", "10:30") in times  # Hiroki's block stays whole
    assert all(s.endTime != "09:36" for s in out)
    hiroki = next(s for s in out if s.startTime == "09:00")
    assert "items total 36 min, block is 90 min" in (hiroki.note or "")


def test_hiroki_v05_actual_cell_has_four_timed_children():
    out = _cell("6G waveform (30)\n10.2.1\n\n6G 10.5.4.x (120)\n"
                "10.5.4.2(20), 10.5.4.1(30), 10.5.4.4(30), 10.5.4.3(40)", 1020, 1170)
    assert [(s.startTime, s.endTime, s.agendaItems) for s in out] == [
        ("17:00", "17:30", ["10.2.1"]), ("17:30", "17:50", ["10.5.4.2"]),
        ("17:50", "18:20", ["10.5.4.1"]), ("18:20", "18:50", ["10.5.4.4"]),
        ("18:50", "19:30", ["10.5.4.3"]),
    ]


def test_timed_wildcard_parent_does_not_double_count_minutes():
    text = "6GR (120)\n.10.5.4.x(120)\n10.5.4.2(20), 10.5.4.1(30), 10.5.4.4(30), 10.5.4.3(40)"
    assert len(_parse_cell(text)) == 1
    assert [s.agendaItems for s in _cell(text, 1050, 1170)] == [
        ["10.5.4.2"], ["10.5.4.1"], ["10.5.4.4"], ["10.5.4.3"],
    ]


def test_wildcard_children_with_mismatched_minutes_remain_untimed():
    out = _cell("6GR (120)\n.10.5.4.x(120)\n10.5.4.2(20), 10.5.4.1(30)", 1050, 1170)
    assert len(out) == 1
    assert (out[0].startTime, out[0].endTime) == ("17:30", "19:30")
    assert all(not s.startTime for s in out[0].agendaBreakdown)
    assert "items total 50 min, block is 120 min" in (out[0].note or "")
