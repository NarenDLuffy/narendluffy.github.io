"""RAN3 rules: chair-notes weekday table (main) + offline room spreadsheet."""

import docx
import openpyxl

from ingestion.groups import group_for
from ingestion.models import Meeting, ScheduleSource
from ingestion.ran3_schedule import (
    ai_codes, chair_notes_re, notes_rank, overlap_problems, parse_chair_grid,
    parse_offline_sheet, pick, resolve_topic,
)

M = Meeting(id="ran3-134", slug="ran3-134", name="RAN3#134", type="regular", startDate="2026-11-16",
            endDate="2026-11-20", timezone="America/Edmonton", status="active")
SRC = ScheduleSource(sourceId="s", meetingId=M.id, fileName="n.docx", label="x", type="main_schedule",
                     origin="public", retrievedAt="")


def _grid(tmp_path, rows):
    d = docx.Document()
    t = d.add_table(rows=len(rows) + 1, cols=3)
    t.cell(0, 1).text, t.cell(0, 2).text = "Monday", "Tuesday"
    for i, r in enumerate(rows, 1):
        for j, v in enumerate(r):
            if v is not None:
                t.cell(i, j).text = v
    return d, t


def _parse(tmp_path, d):
    p = tmp_path / "n.docx"
    d.save(p)
    return parse_chair_grid(str(p), M, SRC)


def test_untimed_row_is_bounded_by_the_breaks(tmp_path):
    d, _ = _grid(tmp_path, [["09:00", "Org: AI 1-8", "6G SI: AI 10.1, 10.3.2"],
                            ["10:30~11:00", "Coffee Break", "Coffee Break"],
                            ["", "Corrections: AI 9", "6G SI: AI 10.2"],
                            ["13:00~14:30", "Lunch Break", "Lunch Break"]])
    _, s, problems = _parse(tmp_path, d)
    tue = [(x.startTime, x.endTime, x.kind, x.agendaItems) for x in s if x.date == "2026-11-17"]
    assert ("11:00", "13:00", "session", ["10.2"]) in tue
    assert ("09:00", "10:30", "session", ["10.1", "10.3.2"]) in tue
    assert problems == []


def test_offline_line_in_break_cell_goes_to_offline_lane(tmp_path):
    d, _ = _grid(tmp_path, [["09:00", "x", "y"], ["10:30~11:00", "Coffee Break", "Coffee Break\n6G Offline (CB#9)"],
                            ["11:00", "z", "w"]])
    _, s, _ = _parse(tmp_path, d)
    lane = [(x.roomName, x.startTime, x.endTime) for x in s if x.topic.startswith("6G Offline")]
    brk = [x for x in s if x.date == "2026-11-17" and x.kind == "break"]
    assert lane == [("6G offline", "10:30", "11:00")] and brk and brk[0].roomName == "Main"


def test_row_without_any_bound_is_a_problem_not_a_guess(tmp_path):
    d, _ = _grid(tmp_path, [["", "Session nobody timed", None]])
    _, s, problems = _parse(tmp_path, d)
    assert s == [] and problems


def test_merged_cell_spans_both_listed_times(tmp_path):
    d, t = _grid(tmp_path, [["08:00", "", "6G Offline*"], ["08:30", "", ""], ["09:00", "Org", "Org"]])
    t.cell(1, 2).merge(t.cell(2, 2))
    _, s, _ = _parse(tmp_path, d)
    off = [(x.startTime, x.endTime) for x in s if x.roomName == "6G offline"]
    assert off == [("08:00", "09:00")]


def test_ai_codes():
    assert ai_codes("Org: AI 1-8") == [str(i) for i in range(1, 9)]
    assert ai_codes("AIML RAN: AI 12/L") == ["12"]
    assert ai_codes("R20 SON/MDT [AI:11.2] (GTW)") == ["11.2"]
    assert ai_codes("CBs") == []


def test_offline_sheet_merges_slots_and_names_room(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Nov19 Thu"
    ws.append([None, "Offline", None])
    ws.append(["Time Slot", "Topic", "Moderator"])
    for slot in ["1130 ~ 1200", "1200 ~ 1230", "1230 ~ 1300"]:
        ws.append([slot, "R20 SON/MDT [AI:11.2] (GTW)", "Ziqiao Liu (CATT)"])
    ws.append(["1300 ~ 1330", "No parallel offlines with main session", None])
    p = tmp_path / "o.xlsx"
    wb.save(p)
    rooms, s, _ = parse_offline_sheet(str(p), M, SRC)
    assert [r.roomName for r in rooms] == ["Offline GTW"]
    assert [(x.date, x.startTime, x.endTime, x.agendaItems, x.sessionLead) for x in s] == [
        ("2026-11-19", "11:30", "13:00", ["11.2"], "Ziqiao Liu (CATT)")]


def test_topic_names_link_to_unique_agenda_item():
    titles = {"13": "Integrated Sensing And Communication for NR (RAN3-led)", "13.1": "General",
              "15": "NR mobility enhancements Phase 5", "12.2": "AI/ML-based mobility"}
    assert resolve_topic("ISAC offline", titles) == "13"
    assert resolve_topic("R20 mobility enhancements", titles) == "15"
    assert resolve_topic("CB: # 9_6GServiceCharacterictics", titles) is None


def test_newest_chair_notes_by_timestamp():
    base = "https://x/Chairs_Notes/"
    urls = [base + n for n in ["RAN3_134_agenda_20261118_1800.docx", "RAN3_134_agenda_20261119_0921.docx",
                               "RAN3_133bis_agenda_20261020_0900.docx"]]
    pat = chair_notes_re(134, False)
    assert pick(urls, lambda n: bool(pat.search(n)), notes_rank).endswith("20261119_0921.docx")


def test_ran3_slug_group():
    assert group_for("ran3-134").key == "RAN3"


def test_overlap_in_one_room_is_a_problem():
    from ingestion.models import Session
    a = Session(sessionId="a", meetingId="m", date="d", day="Mon", startTime="09:00", endTime="10:00",
                roomId="r", roomName="R", topic="A", topicKey="a")
    b = Session(sessionId="b", meetingId="m", date="d", day="Mon", startTime="09:30", endTime="10:30",
                roomId="r", roomName="R", topic="B", topicKey="b")
    assert overlap_problems([a, b])


def test_codes_from_two_lines_in_one_cell():
    assert ai_codes("TEI20: AI 31; 6G SI: AI 10.3.1") == ["31", "10.3.1"]
