from ingestion.sa1_schedule import _lanes, file_re, sa1_codes


def test_lanes_and_timed_line():
    cell = "Breakout 1:\n7.4.9 Computing\nMMS\n(19:15-20:30)\n=====\nBreakout 2:\n7.4.10 IMS+7.4.6 Immersive"
    out = _lanes(cell)
    assert out[0] == ("a", ["7.4.9 Computing"], None)
    assert out[1] == ("a", ["MMS"], (19 * 60 + 15, 20 * 60 + 30))
    assert out[2][0] == "b"
    assert sa1_codes(out[2][1]) == ["7.4.10", "7.4.6"]


def test_codes_only_at_line_start():
    assert sa1_codes(["1. Opening", "6.3 Rel19 and earlier", "Revisions"]) == ["1", "6.3"]


def test_files_of_this_meeting_only():
    pat = file_re(116)
    assert pat.search("Breakout sessions schedule_SA1#116.docx")
    assert pat.search("S1-264002_Agenda for SA1#116_MON_19_00.docx")
    assert not pat.search("Agenda for SA1#1160.docx")
    assert not pat.search("Agenda_Ubiq_TUE.docx")
