from datetime import date

from ingestion.block_schedule import MAIN_FILE_RE
from ingestion.generate_schedule import rebuild_due


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
