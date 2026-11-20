"""Regression: Wednesday 14 Oct 2026, Tamna BC Hall 17:00-19:30 (RAN1#126bis).

The official grid has a Tuesday "Early dinner" sub-row under 17:00 ~ 19:30.
Its other cells are vertical-merge continuations that Word stores without the
lane colour, so they were read a second time as white (Main) cells: Yeongju A's
"Modulation" landed in Tamna BC and the merge dropped 10.4.2 and 10.5.5.
"""

from __future__ import annotations

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from ingestion.block_schedule import parse_block_schedule_docx
from ingestion.live import coverage_gaps
from ingestion.models import Room, ScheduleSource, Session, SessionSourceRef

SRC = ScheduleSource(
    sourceId="s", meetingId="m", fileName="f.docx", label="f", type="x",
    origin="public", retrievedAt="x",
)
FILLS = ["FFFFFF", "D9D9D9"]


def _cell_props(cell, fill: str | None, merge: str | None) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    if fill:
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:fill"), fill)
        tc_pr.append(shd)
    if merge:
        v = OxmlElement("w:vMerge")
        if merge == "restart":
            v.set(qn("w:val"), "restart")
        tc_pr.append(v)


def _grid(path: str) -> None:
    doc = Document()
    doc.add_paragraph("RAN1#126b Online Session Schedule")
    table = doc.add_table(rows=3, cols=3)
    head = table.rows[0].cells
    head[0].text, head[1].text = "", "Wednesday"
    head[1].merge(head[2])
    row = table.rows[1].cells
    row[0].text = "17:00 ~ 19:30 (150 min)"
    row[1].text = "6GR (150)\n.10.4.1 (40)\n.10.4.2 (40)\n.10.5.5 (40)\n.10.5.3.1 (30)"
    row[2].text = "6GR (150)\n.10.3.1 Channel coding (60)\n.10.3.2 Modulation (30)\n.10.5.2.2 (60)"
    _cell_props(row[0], "FFFFFF", "restart")
    _cell_props(row[1], FILLS[0], "restart")
    _cell_props(row[2], FILLS[1], "restart")
    # Continuation sub-row: every cell continues the one above; Word stores
    # them white, losing the lane colour (as in the real file).
    for cell in table.rows[2].cells:
        _cell_props(cell, "FFFFFF", "continue")
    doc.save(path)


def test_continuation_rows_are_not_read_twice(tmp_path):
    path = str(tmp_path / "grid.docx")
    _grid(path)
    rooms, sessions = parse_block_schedule_docx(
        path, meeting_id="m", start_date="2026-10-12", end_date="2026-10-16", source=SRC
    )
    white = next(r for r in rooms if r.sourceColor == "FFFFFF")
    main = sorted(
        (s.startTime, s.endTime, s.agendaItems[0])
        for s in sessions
        if s.roomId == white.roomId and s.date == "2026-10-14" and s.kind == "session"
    )
    assert main == [
        ("17:00", "17:40", "10.4.1"),
        ("17:40", "18:20", "10.4.2"),
        ("18:20", "19:00", "10.5.5"),
        ("19:00", "19:30", "10.5.3.1"),
    ]


def test_all_white_row_keeps_the_three_established_room_lanes(tmp_path):
    """RAN1#127 Friday 11:00: Word paints all three cells white.

    White is genuinely Main's colour elsewhere, but here it is missing formatting
    in the other two lanes. The table-wide lane colours must keep all three rooms.
    """
    path = str(tmp_path / "white-row.docx")
    doc = Document()
    doc.add_paragraph("RAN1#127 Online Session Schedule")
    table = doc.add_table(rows=3, cols=4)
    table.cell(0, 1).merge(table.cell(0, 3))
    table.cell(0, 1).text = "Friday"
    table.cell(1, 0).text = "08:00 ~ 10:30 (150 min)"
    table.cell(2, 0).text = "11:00 ~ 12:30 (90 min)"
    morning = ["Main session\n10.5.1 (150)", "10.7.1 (150)", "10.8 (150)"]
    after_coffee = [
        "Sweep",
        "6GR (90)\n.10.5.2.2 (30)\n.10.5.2.3 (60)",
        "6GR (TBD)\n.10.8 Sensing (TBD)",
    ]
    for lane, fill in enumerate(["FFFFFF", "D9D9D9", "FFD966"], 1):
        table.cell(1, lane).text = morning[lane - 1]
        table.cell(2, lane).text = after_coffee[lane - 1]
        _cell_props(table.cell(1, lane), fill, None)
        _cell_props(table.cell(2, lane), "FFFFFF", None)
    doc.save(path)

    rooms, sessions = parse_block_schedule_docx(
        path, meeting_id="m", start_date="2026-11-16", end_date="2026-11-20", source=SRC
    )
    by_colour = {room.sourceColor: room.roomId for room in rooms}
    published = [
        (s.roomId, s.startTime, s.endTime, s.agendaItems)
        for s in sessions if s.startTime >= "11:00"
    ]
    assert len({room_id for room_id, *_ in published}) == 3
    assert (by_colour["D9D9D9"], "11:00", "11:30", ["10.5.2.2"]) in published
    assert (by_colour["D9D9D9"], "11:30", "12:30", ["10.5.2.3"]) in published
    assert (by_colour["FFD966"], "11:00", "12:30", ["10.8"]) in published
    assert (by_colour["FFFFFF"], "11:00", "12:30", []) in published


def test_unnamed_white_detail_table_does_not_displace_main(tmp_path):
    """Sorour's one-room table is white but belongs to Room 225-226, not Main."""
    from ingestion.canonical_schedule import canonicalize
    from ingestion.room_resolver import resolve_rooms

    path = str(tmp_path / "unnamed-detail.docx")
    doc = Document()
    doc.add_paragraph("RAN1#127 Online Session Schedule")
    grid = doc.add_table(rows=4, cols=3)
    grid.cell(0, 1).merge(grid.cell(0, 2))
    grid.cell(0, 1).text = "Friday"
    rows = [
        ("08:00 ~ 09:00 (60 min)", "RAN1#127 commences\nMain session\n10.5.1 (60)", "10.7.1 (60)", "10.7.1 NTN (60)"),
        ("09:00 ~ 10:00 (60 min)", "Main session\n10.5.2 (60)", "10.5.2.2 (60)", "10.5.2.2 PDSCH (60)"),
        ("11:00 ~ 12:30 (90 min)", "Sweep", "6GR (90)\n.10.5.2.3 (90)", "6GR (90)\nAI 10.5.2.3 PUxCH (90)"),
    ]
    for row_index, (time, main, grey, _) in enumerate(rows, 1):
        grid.cell(row_index, 0).text = time
        grid.cell(row_index, 1).text = main
        grid.cell(row_index, 2).text = grey
        _cell_props(grid.cell(row_index, 1), "FFFFFF", None)
        _cell_props(grid.cell(row_index, 2), "D9D9D9", None)

    doc.add_paragraph("RAN1#127 Detailed Schedule for Sorour’s RAN1 Session")
    detail = doc.add_table(rows=4, cols=2)
    detail.cell(0, 1).text = "Friday"
    for row_index, (time, _, _, detail_text) in enumerate(rows, 1):
        detail.cell(row_index, 0).text = time
        detail.cell(row_index, 1).text = detail_text
        _cell_props(detail.cell(row_index, 1), "FFFFFF", None)
    doc.save(path)
    source = ScheduleSource(
        sourceId="main", meetingId="m", fileName="RAN1#127 online and offline schedules - v04.docx",
        label="main", type="main_schedule", origin="public", retrievedAt="now",
    )

    rooms, sessions = parse_block_schedule_docx(
        path, meeting_id="m", start_date="2026-11-16", end_date="2026-11-20", source=source
    )
    rooms, sessions = resolve_rooms("m", rooms, sessions)
    result = canonicalize(sessions)
    main_id = next(room.roomId for room in rooms if room.chairRole == "main")
    grey_id = next(room.roomId for room in rooms if room.sourceColor == "D9D9D9")
    after_coffee = [s for s in result.sessions if s.startTime == "11:00"]
    assert {(s.roomId, s.topic, tuple(s.agendaItems)) for s in after_coffee} == {
        (main_id, "Sweep", ()),
        (grey_id, "10.5.2.3", ("10.5.2.3",)),
    }


def _s(start: str, end: str, room: str = "r", code: str = "10.4.1") -> Session:
    return Session(
        sessionId=f"{room}{start}", meetingId="m", date="2026-10-14", day="Wednesday",
        startTime=start, endTime=end, roomId=room, roomName="Tamna BC Hall", topic=code,
        topicKey=code, agendaItems=[code], kind="session", status="scheduled",
        sources=[SessionSourceRef("s", ["time"])],
    )


def test_a_dropped_item_is_reported_as_a_gap():
    rooms = [Room(roomId="r", meetingId="m", roomName="Tamna BC Hall", order=0)]
    parsed = [_s("17:00", "17:40"), _s("17:40", "18:20"), _s("18:20", "19:00"), _s("19:00", "19:30")]
    published = [_s("17:00", "17:40"), _s("19:00", "19:30")]
    gaps = coverage_gaps(parsed, published, rooms)
    assert gaps == [
        "2026-10-14 Tamna BC Hall: no session 17:40-19:00 although a schedule document fills it"
    ]
    assert coverage_gaps(parsed, parsed, rooms) == []


def test_one_cell_read_into_two_rooms_is_refused():
    from dataclasses import replace

    from ingestion.live import cell_checks

    rooms = [
        Room(roomId="r", meetingId="m", roomName="Tamna BC Hall", order=0),
        Room(roomId="y", meetingId="m", roomName="Yeongju A Hall", order=1),
    ]
    good = _s("18:00", "18:30", room="y", code="10.3.2")
    good.sources = [SessionSourceRef("s", ["time"], cell="s|t3|Wednesday|1020|c2|ab")]
    copy = replace(good, roomId="r", sources=[SessionSourceRef("s", ["time"], cell=good.sources[0].cell)])
    errors = cell_checks([good, copy], [good, copy], rooms)
    assert any("one table cell was read into 2 rooms" in e for e in errors)
    assert any("10.3.2 is in both" in e for e in errors)
    assert cell_checks([good], [good], rooms) == []


def test_item_listed_in_two_rooms_by_the_document_is_allowed():
    from ingestion.live import cell_checks

    rooms = [
        Room(roomId="r", meetingId="m", roomName="Tamna BC Hall", order=0),
        Room(roomId="y", meetingId="m", roomName="Yeongju A Hall", order=1),
    ]
    a = _s("18:00", "18:30", room="r", code="10.3.2")
    a.sources = [SessionSourceRef("s", ["time"], cell="s|t3|Wednesday|1020|c1|aa")]
    b = _s("18:00", "18:30", room="y", code="10.3.2")
    b.sources = [SessionSourceRef("s", ["time"], cell="s|t3|Wednesday|1020|c2|bb")]
    assert cell_checks([a, b], [a, b], rooms) == []


def test_overlapping_published_blocks_in_one_room_are_refused():
    from ingestion.live import cell_checks

    rooms = [Room(roomId="r", meetingId="m", roomName="Room 225-226", order=0)]
    a = _s("09:50", "10:30", code="10.3.1")
    b = _s("09:50", "10:30", code="9.4")
    b.topic = "NTN-NR"
    errors = cell_checks([], [a, b], rooms)
    assert any("overlapping published blocks" in e and "NTN-NR" in e for e in errors)
    assert cell_checks([], [_s("09:20", "09:50"), _s("09:50", "10:30")], rooms) == []


def test_granularity_audit_catches_a_complete_fresh_chair_tiling():
    from ingestion.live import granularity_checks

    rooms = [Room(roomId="r", meetingId="m", roomName="Room 214-215", order=0)]
    main = _s("11:00", "12:30", code="10.8")
    main.sources = [SessionSourceRef(
        "main", ["main-authority"], introducedAt="2026-11-20T09:00:00Z",
    )]
    details = [
        _s("11:00", "11:05", code="11"),
        _s("11:05", "11:15", code="10.2.1"),
        _s("11:15", "12:30", code="10.8.1"),
    ]
    details[-1].agendaItems = ["10.8.1", "10.8.2", "10.8.3"]
    for detail in details:
        detail.sources = [SessionSourceRef(
            "hh7", ["own-table"], cell="hh7|t5|Friday|660|c5|20f39b3c",
            introducedAt="2026-11-20T10:00:00Z",
        )]

    errors = granularity_checks([main, *details], [main], rooms)
    assert len(errors) == 1
    assert "11:00-11:05 11" in errors[0]
    assert "11:15-12:30 10.8.1, 10.8.2, 10.8.3" in errors[0]

    main.sources[0].introducedAt = "2026-11-20T11:00:00Z"
    assert granularity_checks([main, *details], [main], rooms) == []
