from ingestion.ran4_schedule import codes_for, split_cell, topic_ids


def spans(lines):
    return [(s.start, s.end, s.kind, s.lines[0]) for s in split_cell(lines)]


def test_dash_time_line_splits_cell():
    out = spans(["Main Ad-hoc", "[105-A] 6G RRM", "—12:00—", "[105-B] 6G RRM"])
    assert out == [(None, 720, "", "Main Ad-hoc"), (720, None, "", "[105-B] 6G RRM")]


def test_timed_headings_in_one_cell():
    out = spans(["BR2 Ad-hoc: 5G BSRF (14:30 – 15:30)", "[345] NR_BS_RF_Ph2", "",
                 "BR1 Ad-hoc: 6G testability/OTA (15:30-16:30)", "[219] 6G_testability_OTA"])
    assert [(a, b) for a, b, _k, _l in out] == [(870, 930), (930, 990)]


def test_coffee_break_adhoc_is_its_own_break_part():
    out = spans(["[102] General RF", "", "Coffeebreak AH: [101-B] System Parameter by Jinqiang (OPPO)"])
    assert out[1][2] == "coffee" and out[1][3] == "[101-B] System Parameter by Jinqiang (OPPO)"


def test_bracketed_lunch_adhoc_keeps_its_written_time():
    out = spans(["6G EARLY RETURN TO", "", "[Lunch break AH] 13.10-14.20: Joint RAN4/5 session"])
    assert out[1][:3] == (790, 860, "lunch") and out[1][3] == "Joint RAN4/5 session"


def test_timed_lines_inside_a_timed_heading_split_it():
    out = spans(["BR2 Ad-hoc: TN – NTN handover (8:00 – 9:00)", "[349] handover (8:00 – 8:30)", "[306] TEI (8:30 – 9:00)"])
    assert [(a, b) for a, b, _k, _l in out] == [(480, 510), (510, 540)]


def test_topic_numbers_map_through_the_topic_list():
    topics = {"105-A": ["8.6"], "105-B": ["8.6.1"], "201": ["7.4.2"]}
    assert topic_ids("[105-A/B] 6G RRM") == ["105-A", "105-B"]
    assert codes_for("[105] 6G RRM", topics) == ["8.6", "8.6.1"]
    assert codes_for("107] 6G AI / [201] NR_RRM_Ph6", topics) == ["7.4.2"]
    assert codes_for("[11x] TEI20", topics) == []
