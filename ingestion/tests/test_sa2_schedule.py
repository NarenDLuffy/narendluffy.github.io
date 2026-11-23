from ingestion.sa2_schedule import plan_rank, plan_re, sa2_codes


def test_codes_only_from_written_numbers():
    assert sa2_codes("KI#18 (AI for Network) (20.6.18) [9]") == ["20.6.18"]
    assert sa2_codes("KI#12 – KI#16 (20.6.12 – 16) [7]") == ["20.6.12", "20.6.13", "20.6.14", "20.6.15", "20.6.16"]
    assert sa2_codes("6G Single Stream (20.6.x)") == ["20.6"]
    assert sa2_codes("Opening (1), Agenda (2)\n20.48, 20.49 [14]") == ["1", "2", "20.48", "20.49"]
    assert sa2_codes("KI#23 NTN (20.6.23) [2\n5GSAT_Ph4-ARC (20.1.2) [2]") == ["20.6.23", "20.1.2"]


def test_newest_revision_of_this_meeting_only():
    pat = plan_re(178)
    names = ["S2-2611637_SA2-178-Session Plan - r9.docx", "S2-2611637_SA2-178-Session Plan - r19.docx",
             "S2-2611637_SA2-178-Session Plan - r7.zip", "S2-2609999_SA2-177-Session Plan - r30.docx"]
    hits = [n for n in names if pat.search(n)]
    assert "S2-2609999_SA2-177-Session Plan - r30.docx" not in hits
    assert max(hits, key=plan_rank).endswith("r19.docx")
