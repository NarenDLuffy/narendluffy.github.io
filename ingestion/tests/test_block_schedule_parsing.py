from ingestion.block_schedule import _parse_cell


def test_timed_parent_is_container_for_explicit_timed_children():
    segments = _parse_cell(
        "6GR (120)\n.10.5.4 (120)\n\n"
        ".10.5.4.1 (50)\n.10.5.4.2 (25)\n.10.5.4.3 (40)\n.10.5.4.4 (35)"
    )
    assert len(segments) == 1
    assert [slot.label for slot in segments[0].slots] == [
        "10.5.4.1",
        "10.5.4.2",
        "10.5.4.3",
        "10.5.4.4",
    ]
    assert [slot.minutes for slot in segments[0].slots] == [50, 25, 40, 35]