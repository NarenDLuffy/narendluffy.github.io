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
