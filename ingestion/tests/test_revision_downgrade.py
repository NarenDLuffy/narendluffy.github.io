from ingestion.generate_schedule import revision_downgrades


def test_older_revision_after_meeting_is_refused():
    before = [{"fileName": "RAN1#126bis schedule for Hiroki Adhoc2 sessions_v06.docx"}]
    after = [{"fileName": "RAN1#126bis schedule for Hiroki Adhoc2 sessions_v01.docx"}]
    assert revision_downgrades(before, after)


def test_dropped_family_is_refused():
    before = [{"fileName": "RAN1#126b Sorour sessions online and offline schedules - v05.docx"}]
    assert revision_downgrades(before, [])


def test_official_replacing_draft_is_allowed():
    before = [{"fileName": "Draft RAN1#127 online and offline schedules - v03.docx"}]
    after = [{"fileName": "RAN1#127 online and offline schedules - v00.docx"}]
    assert revision_downgrades(before, after) == []


def test_newer_revision_is_allowed():
    before = [{"fileName": "Chair notes RAN1#127_v02.docx"}]
    after = [{"fileName": "Chair notes RAN1#127_v03.docx"}]
    assert revision_downgrades(before, after) == []
