from ingestion.topic_agenda_mapper import map_topic

AGENDA = [
    ("8", "Maintenance on Rel-19 NR and E-UTRA"),
    ("8.1", "Maintenance on AI/ML for NR Air interface, NR MIMO Phase 5"),
    ("9", "Release 20 NR"),
    ("9.1", "Artificial Intelligence (AI)/Machine Learning (ML) for NR air interface enhancements"),
    ("9.2", "NR MIMO Phase 6"),
    ("9.3", "Solutions for Ambient IoT (Internet of Things) in NR Phase 2"),
    ("9.4", "GNSS resilient NR-NTN operation"),
    ("9.5", "NR NTN in systems using downlink compensation"),
]


def test_links_unique_topics():
    assert map_topic("R20 AI/ML", AGENDA) == "9.1"
    assert map_topic("R20 MIMO", AGENDA) == "9.2"
    assert map_topic("A-IoT Phase2", AGENDA) == "9.3"


def test_ambiguous_and_breaks_unlinked():
    assert map_topic("NTN-NR", AGENDA) is None
    assert map_topic("Morning coffee break", AGENDA) is None
