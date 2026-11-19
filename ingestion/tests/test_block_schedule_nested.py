from ingestion.block_schedule import _parse_cell


def _slots(text):
    return [[(s.label, s.minutes) for s in g.slots] for g in _parse_cell(text)]


def test_child_fills_its_parent_item():
    # Hiroki RAN1#127 Thursday: 10.8 Sensing (50) is 10.8.3 for those 50 minutes.
    out = _slots("6GR (110)\n.10.8 Sensing (50)\n 10.8.3 (50)\n\n.10.5.4.1 (60)")
    assert out[0] == [("10.8.3", 50), ("10.5.4.1", 60)]


def test_named_item_takes_its_code():
    out = _slots("R20 (60)\nA-IoT Phase2 (60)\n 9.3.3 (60)")
    assert out == [[("9.3.3", 60)]]


def test_children_that_do_not_fill_parent_are_left_alone():
    out = _slots("6GR (120)\n.10.5.1 Waveform (30)\n.10.8 Sensing (90)\n10.8.1 (30)\n10.8.2 (30)")
    assert ("10.8 Sensing", 90) in out[0]


def test_untimed_items_under_timed_head_keep_their_codes():
    # Hiroki RAN1#127 hh4 Thursday, BMO 214-215: no minutes, so no split, but all items listed.
    groups = _parse_cell("TEI, AI 7/8.1 (40)\n7 pre-Rel-19 CRs\n8.1 Duplex\n8.1 Mobility\n11 TEI20")
    assert [c for s in groups[0].slots for c in s.codes] == ["7", "8.1", "8.1", "11"]


def test_code_lines_after_short_head_are_their_own_blocks():
    # Sorour RAN1#127 v04 Friday Room 225-226.
    groups = _parse_cell("[TBD\xa0: AI/ML,MIMO]? (20)\n9.5 NTN (30)\n10.7.1 NTN (30)\n9.4 NR-NTN (40)\n.10.5.2.2 (30)")
    assert [g.minutes for g in groups][:4] == [20, 30, 30, 40]
