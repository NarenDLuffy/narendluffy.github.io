"""The main online/offline grid owns times, rooms, and breaks everywhere."""

from ingestion.canonical_schedule import canonicalize
from ingestion.live import coverage_gaps
from ingestion.models import AgendaSlot, Room, Session, SessionSourceRef


def make(
    start: str,
    end: str,
    *,
    source: str,
    items: list[str] | None = None,
    room: str = "room-a",
    authority: bool = False,
    kind: str = "session",
    topic: str = "Session",
    breakdown: list[tuple[str, str, str]] | None = None,
) -> Session:
    return Session(
        sessionId=f"{source}-{room}-{start}-{kind}",
        meetingId="m",
        date="2026-11-16",
        day="Monday",
        startTime=start,
        endTime=end,
        roomId="" if kind in {"lunch", "break"} else room,
        roomName="" if kind in {"lunch", "break"} else room,
        topic=topic,
        topicKey=kind,
        agendaItems=items or [],
        agendaBreakdown=[
            AgendaSlot(code=code, label=code, startTime=slot_start, endTime=slot_end)
            for code, slot_start, slot_end in (breakdown or [])
        ],
        kind=kind,
        sources=[SessionSourceRef(source, ["main-authority"] if authority else ["own-table"])],
    )


def test_main_grid_controls_all_rooms_and_times_but_accepts_inner_detail():
    main = make("11:00", "12:30", source="main", items=["10.5"], authority=True)
    detail = make(
        "11:00",
        "12:30",
        source="hiroki",
        items=["10.5"],
        breakdown=[("10.5.4.1", "11:00", "11:40"), ("10.5.4.4", "11:40", "12:30")],
    )
    stale_extra = make("12:30", "13:00", source="hiroki", items=["9.1"])
    chair_only_room = make("11:00", "12:00", source="sorour", items=["8.2"], room="room-b")

    result = canonicalize([detail, stale_extra, chair_only_room, main])

    assert [(s.startTime, s.endTime, s.agendaItems, s.roomId) for s in result.sessions] == [
        ("11:00", "11:40", ["10.5.4.1"], "room-a"),
        ("11:40", "12:30", ["10.5.4.4"], "room-a"),
    ]


def test_other_files_leftover_container_never_displaces_a_main_grid_child():
    main = make(
        "11:00", "12:30", source="main", items=["10.5"], authority=True,
        breakdown=[("10.5.1", "11:00", "11:40"), ("10.5.2", "11:40", "12:30")],
    )
    copied_broad_container = make("11:00", "12:30", source="sorour", items=["10.5"])
    partial_detail = make("11:00", "11:40", source="hiroki", items=["10.5.1"])

    result = canonicalize([copied_broad_container, partial_detail, main])

    assert [(s.startTime, s.endTime, s.agendaItems) for s in result.sessions] == [
        ("11:00", "11:40", ["10.5.1"]),
        ("11:40", "12:30", ["10.5.2"]),
    ]


def test_main_grid_item_wins_over_a_stale_copy_in_a_breakout_room():
    main = make("12:30", "13:00", source="main", items=["10.5.3.4"], authority=True)
    stale = make("12:30", "13:00", source="sorour", items=["10.5.3.2"])

    result = canonicalize([stale, main])

    assert len(result.sessions) == 1
    assert result.sessions[0].agendaItems == ["10.5.3.4"]
    assert "Another schedule file lists 10.5.3.2" in (result.sessions[0].note or "")


def test_main_grid_lunch_replaces_different_chair_lunch_times():
    main_lunch = make(
        "12:30", "14:00", source="main", authority=True, kind="lunch", topic="Lunch break"
    )
    chair_lunch = make(
        "13:00", "14:30", source="hiroki", kind="lunch", topic="Lunch break"
    )

    result = canonicalize([chair_lunch, main_lunch])

    assert [(s.startTime, s.endTime, s.kind) for s in result.sessions] == [
        ("12:30", "14:00", "lunch")
    ]
    assert [ref.sourceId for ref in result.sessions[0].sources] == ["main"]


def test_chair_only_time_outside_main_frame_is_not_a_coverage_gap():
    main = make("11:00", "12:30", source="main", items=["10.5"], authority=True)
    stale_extra = make("12:30", "13:00", source="hiroki", items=["9.1"])
    rooms = [Room(roomId="room-a", meetingId="m", roomName="Room A", order=0)]

    assert coverage_gaps([main, stale_extra], [main], rooms) == []
    assert coverage_gaps([main, stale_extra], [], rooms) == [
        "2026-11-16 Room A: no session 11:00-12:30 although a schedule document fills it"
    ]
