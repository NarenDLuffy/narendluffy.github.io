from draft_tracker.sa_tdocs import file_code, folder_code, tdocs_in

TL = {"S1-264378": "7.4.3", "S1-264097": "5", "S2-2612106": "20.6.6"}
CODES = {
    "20.2.1": "Study on ISAC (FS_Sensing_ARC)", "20.2.2": "ISAC (Sensing_ARC)",
    "20.6.1": "Study on 6G (FS_6G_ARC) - NAS", "20.6.2": "Study on 6G (FS_6G_ARC) - SBA",
    "19.14.2": "Ambient IoT (AmbientIoT-ARC)", "20.5.2": "Ambient IoT Phase 2 (AmbientIoT_Ph2-ARC)",
}


def test_file_by_own_then_previous_tdoc():
    assert file_code("draft S1-264378 was 4113 AI Training.docx", TL) == "7.4.3"
    assert file_code("draftS1-264305_was4097-CR_22101.docx", TL) == "5"
    assert file_code("S2-2612574_was_S2-2612106 KI-6.docx", TL) == "20.6.6"
    assert file_code("Group photo.jpg", TL) is None
    assert tdocs_in("S2-2612792 was 12624 was 12238_KI20.docx") == ["S2-2612792", "S2-2612624", "S2-2612238"]


def test_folder_by_work_item_acronym():
    assert folder_code("R20 Sensing-ARC", CODES) == "20.2.2"
    assert folder_code("FS_6G_ARC", CODES) == "20.6"
    assert folder_code("R20 Ambient IoT", CODES) == "20.5.2"
    assert folder_code("R21 IHAT SID", CODES) is None
    assert folder_code("Welcome to Calgary", CODES) is None
