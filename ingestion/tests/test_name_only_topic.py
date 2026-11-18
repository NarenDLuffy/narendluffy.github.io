from ingestion.block_schedule import _parse_cell
from ingestion.topic_agenda_mapper import map_topic

CELL = "R20  (60)\nNTN-NR  (40)\n.9.5  NTN  (20) |\n6GR  (90)\n.10.7.1  NTN  (40)\n.10.3.1  Channel coding  (50)"
AGENDA = [("9", "Release 20 NR"), ("9.4", "GNSS resilient NR-NTN operation"),
          ("9.5", "NR NTN in systems using downlink compensation"),
          ("10", "Release 20 6G Radio"), ("10.7", "NTN")]


def test_pipe_closes_head_and_name_only_item_is_kept():
    segs = _parse_cell(CELL)
    assert [(s.group, s.minutes) for s in segs] == [("R20", 60), ("6GR", 90)]
    assert [(x.label, x.minutes) for x in segs[0].slots] == [("NTN-NR", 40), ("9.5  NTN", 20)]
    assert all(x.group == "6GR" for x in segs[1].slots)


def test_ntn_nr_maps_to_the_item_not_listed_beside_it():
    assert map_topic("R20 NTN-NR", AGENDA, {"9.5"}) == "9.4"


def test_ntn_nr_without_context_is_not_guessed():
    assert map_topic("R20 NTN-NR", AGENDA) is None
