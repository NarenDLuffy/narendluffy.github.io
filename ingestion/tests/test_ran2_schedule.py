"""RAN2 single-grid rules (one schedule DOCX per meeting)."""

from ingestion.groups import group_for
from ingestion.portal import _https_folder
from ingestion.ran2_schedule import _codes, pick_latest, schedule_file_re, split_cell


def test_slot_without_written_times_stays_one_block():
    segs = split_cell("[9.3.1] User Plane\n[9.3.1.2] QoS, QoE", "08:30", "10:30")
    assert [(s["start"], s["end"]) for s in segs] == [(510, 630)]


def test_split_only_at_chair_written_time():
    segs = split_cell("[8.14] TEI20\n\n@9:00  [9.4.2] measurements", "08:30", "10:30")
    assert [(s["start"], s["end"]) for s in segs] == [(510, 540), (540, 630)]


def test_compact_hhmm_range_is_a_time():
    segs = split_cell("1430-1530 MAC open issues (vivo)", "14:30", "16:30")
    assert (segs[0]["start"], segs[0]["end"]) == (870, 930)


def test_budget_and_email_numbers_are_not_agenda_items():
    assert _codes("[8.2] NR20 AIoT [2]") == ["8.2"]
    assert _codes("@10-11 [AT136][004] RRC modeling (Samsung)") == []
    assert _codes("[1], [2], [3],") == ["1", "2", "3"]


def test_newest_revision_of_this_meeting_only():
    urls = [f"https://x/Agenda/R2_136_Schedule_v0{i}.docx" for i in range(8)] + [
        "https://x/Agenda/R2_135_Schedule_v09.docx",
        "https://x/Agenda/R2_136bis_Schedule_v09.docx",
    ]
    assert pick_latest(urls, schedule_file_re(136, False)).endswith("R2_136_Schedule_v07.docx")
    assert pick_latest(urls, schedule_file_re(136, True)).endswith("R2_136bis_Schedule_v09.docx")


def test_group_from_slug_and_docs_folder():
    assert group_for("ran2-136").key == "RAN2"
    assert group_for("ran1-127").key == "RAN1"
    assert _https_folder("https://www.3gpp.org/ftp/tsg_ran/WG2_RL2/TSGR2_136/Docs/").endswith("TSGR2_136/")
