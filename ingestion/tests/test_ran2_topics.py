from ingestion.ran2_topics import folder_topic, resolve_topic
from draft_tracker.agenda_mapper import AgendaMapper

AGENDA = {
    "7.2": "Ambient IoT", "8.2": "Ambient IoT Ph2", "8.2.4": "Topology 2",
    "8.3": "AI/ML for mobility", "9.3.2.1": "RRC Modelling and connection management",
    "9.5": "ISAC", "9.3.1": "User plane",
}


def test_name_only_blocks():
    assert resolve_topic("RRC modeling (Samsung)", AGENDA) == "9.3.2.1"
    assert resolve_topic("A-IoT offline (vivo)", AGENDA) == "8.2"
    assert resolve_topic("ISAC offline (Xiaomi)", AGENDA) == "9.5"


def test_unclear_stays_unlinked():
    assert resolve_topic("offlines", AGENDA) is None
    assert resolve_topic("CB Kyeongin", AGENDA) is None


def test_folder_tags():
    assert folder_topic("[AT136][401][AIoT] Intermediate result (vivo)") == "AIoT"
    assert resolve_topic(folder_topic("[AT136][401][AIoT] x"), AGENDA) == "8.2"
    assert resolve_topic(folder_topic("[AT136][xxx] ISAC pre-meeting offline"), AGENDA) == "9.5"


def test_mapper_tag_only_when_resolver_given():
    name = "[AT136][104][AI-MOB] (OPPO)"
    plain = AgendaMapper(AGENDA).map_folder(name, None)
    assert plain.agenda_item_id is None  # RAN1 behaviour unchanged
    ran2 = AgendaMapper(AGENDA, lambda n: resolve_topic(folder_topic(n), AGENDA)).map_folder(name, None)
    assert ran2.agenda_item_id == "8.3"
