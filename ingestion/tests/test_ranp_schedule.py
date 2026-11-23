from ingestion.models import Session
from ingestion.ranp_schedule import _lanes, _trim_breaks, plan_rank, time_plan_re


def test_lanes_split_main_and_breakout_with_continuation_and_inline_time():
    cell = "Main (12:30~13:30): TBD\nBreakout (12:30~13:30): NTN time/frequency compensation"
    lanes = _lanes(cell)
    assert lanes["main"] == []  # TBD carries nothing
    assert lanes["breakout"] == [("NTN time/frequency compensation", (750, 810))]


def test_plain_text_is_the_plenary_and_main_room_note_forces_main():
    lanes = _lanes("Early items\n1st sweep")
    assert [l for l, _ in lanes["main"]] == ["Early items", "1st sweep"]
    lanes = _lanes("6G spec modernization (12:30~13:30 in RAN main room)")
    assert lanes["main"] == [("6G spec modernization", (750, 810))]


def test_breakout_continuation_lines_stay_in_breakout():
    lanes = _lanes("Main: ITU Adhoc (8:00~9:00)\nBreakout: Rel-21 5G-Adv\n(AI 15.2 – RAN1/2/3 Others)")
    assert [l for l, _ in lanes["breakout"]] == ["Rel-21 5G-Adv", "(AI 15.2 – RAN1/2/3 Others)"]
    assert [l for l, _ in lanes["main"]] == ["ITU Adhoc"]


def _s(start, end, kind="session"):
    return Session(sessionId=start + kind, meetingId="ran-113", date="2026-09-15", day="Tuesday",
                   startTime=start, endTime=end, roomId="main", roomName="Main", topic=kind, topicKey=kind, kind=kind)


def test_meeting_during_lunch_shortens_the_lunch_not_stacked():
    out = _trim_breaks([_s("12:30", "14:00", "lunch"), _s("12:30", "13:30")])
    lunch = next(s for s in out if s.kind == "lunch")
    assert (lunch.startTime, lunch.endTime) == ("13:30", "14:00")


def test_time_plan_name_must_carry_the_meeting_number_and_highest_version_wins():
    pat = time_plan_re(113)
    assert pat.search("RAN#113 time plan v09.zip")
    assert not pat.search("RAN#112 time plan v09.zip")
    assert plan_rank("RAN#113 time plan v10.zip") > plan_rank("RAN#113 time plan v09.docx")
