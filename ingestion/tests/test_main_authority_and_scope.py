from datetime import date

from docx import Document

from ingestion.block_schedule import MAIN_FILE_RE, parse_block_schedule_docx
from ingestion.canonical_schedule import canonicalize
from ingestion.generate_schedule import rebuild_due
from ingestion.models import ScheduleSource


def test_main_file_is_the_shared_grid_only():
    assert MAIN_FILE_RE.match("Draft RAN1#127 online and offline schedules - v02")
    assert MAIN_FILE_RE.match("RAN1#126b online and offline schedules - v00")
    assert not MAIN_FILE_RE.match("Draft RAN1#127 online and offline schedules - v02_hh")
    assert not MAIN_FILE_RE.match("RAN1#127 Sorour sessions online and offline schedules - v00")


def test_finished_meetings_are_not_rebuilt_automatically():
    today = date(2026, 11, 16)
    assert rebuild_due("2026-11-20", today)
    assert rebuild_due("2026-11-15", today)  # the day after still refreshes
    assert not rebuild_due("2026-10-16", today)
    assert rebuild_due("2026-10-16", today, force=True)


def test_main_grid_lunch_beats_the_detail_table_lunch_in_the_same_docx(tmp_path):
    path = str(tmp_path / "main.docx")
    doc = Document()
    for heading, lunch in (
        ("RAN1#127 Online Session Schedule", "Lunch break: 12:30 ~ 14:00"),
        ("RAN1#127 Detailed Schedule for RAN1 Main Session", "Lunch break: 13:00 ~ 14:30"),
    ):
        doc.add_paragraph(heading)
        table = doc.add_table(rows=3, cols=2)
        table.cell(0, 1).text = "Monday"
        table.cell(1, 0).text = "11:00 ~ 12:30 (90 min)"
        table.cell(1, 1).text = "Main session\n10.5 (90)"
        table.cell(2, 0).text = lunch
        table.cell(2, 1).text = lunch
    doc.save(path)
    source = ScheduleSource(
        sourceId="main", meetingId="m", fileName="RAN1#127 online and offline schedules - v00.docx",
        label="main", type="main_schedule", origin="public", retrievedAt="now",
    )

    _, parsed = parse_block_schedule_docx(
        path, meeting_id="m", start_date="2026-11-16", end_date="2026-11-20", source=source
    )
    lunches = [s for s in parsed if s.kind == "lunch"]
    assert {(s.startTime, s.endTime) for s in lunches} == {("12:30", "14:00"), ("13:00", "14:30")}
    grid = next(s for s in lunches if s.startTime == "12:30")
    detail = next(s for s in lunches if s.startTime == "13:00")
    assert "main-authority" in grid.sources[0].contributed
    assert "main-authority" not in detail.sources[0].contributed
    assert "own-table" in detail.sources[0].contributed

    result = canonicalize(parsed)
    canonical_lunches = [s for s in result.sessions if s.kind == "lunch"]
    assert len(canonical_lunches) == 5  # one per meeting day, not two competing times
    assert {(s.startTime, s.endTime) for s in canonical_lunches} == {("12:30", "14:00")}


def test_multilane_grid_with_floating_room_labels_keeps_main_authority(tmp_path):
    path = str(tmp_path / "main-with-labels.docx")
    doc = Document()
    doc.add_paragraph("RAN1#127 Online Session Schedule Champions Ballroom A BMO 214-215")
    table = doc.add_table(rows=3, cols=3)
    table.cell(0, 1).merge(table.cell(0, 2))
    table.cell(0, 1).text = "Monday"
    table.cell(1, 0).text = "11:00 ~ 12:30 (90 min)"
    table.cell(1, 1).text = "Main session\n10.5 (90)"
    table.cell(1, 2).text = "10.4.1 (90)"
    for col in range(3):
        table.cell(2, col).text = "Lunch break: 12:30 ~ 14:00"
    doc.save(path)
    source = ScheduleSource(
        sourceId="main", meetingId="m", fileName="RAN1#127 online and offline schedules - v00.docx",
        label="main", type="main_schedule", origin="public", retrievedAt="now",
    )

    _, parsed = parse_block_schedule_docx(
        path, meeting_id="m", start_date="2026-11-16", end_date="2026-11-20", source=source
    )

    assert parsed
    assert all(
        "main-authority" in ref.contributed and "own-table" not in ref.contributed
        for session in parsed for ref in session.sources
    )
