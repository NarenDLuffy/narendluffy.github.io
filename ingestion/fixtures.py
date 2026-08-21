"""Two independent meeting fixtures used to prove the app is meeting-agnostic.

Fixture A mirrors a real RAN1 plenary (dates, venue, room count, agenda codes).
Fixture B is a completely synthetic ad-hoc meeting in a different timezone,
with a different number of days, different room names and different agenda
codes. Both are produced by the *same* generator: if anything in the app were
hard coded to one meeting, fixture B would break visibly.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone

from .meeting_discovery import compute_status
from .models import (
    AgendaItem,
    IngestStatus,
    Meeting,
    MeetingSourceFolders,
    Room,
    ScheduleBundle,
    ScheduleChange,
    ScheduleSource,
    Session,
    SessionSourceRef,
)

NOW = datetime.now(timezone.utc).replace(microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _topic_key(topic: str) -> str:
    return hashlib.sha1(topic.lower().encode()).hexdigest()[:8]


def build_meeting(
    *,
    slug: str,
    name: str,
    kind: str,
    number: int | None,
    start: date,
    days: int,
    tz: str,
    city: str,
    country: str,
    venue: str,
    rooms: list[tuple[str, str]],
    agenda: list[tuple[str, str, str | None]],
    doc_names: list[str],
) -> ScheduleBundle:
    end = start + timedelta(days=days - 1)
    meeting = Meeting(
        id=slug,
        slug=slug,
        name=name,
        type=kind,  # type: ignore[arg-type]
        startDate=start.isoformat(),
        endDate=end.isoformat(),
        timezone=tz,
        status=compute_status(start.isoformat(), end.isoformat()),  # type: ignore[arg-type]
        meetingNumber=number,
        city=city,
        country=country,
        venue=venue,
        schedulePublished=True,
        sources=MeetingSourceFolders(
            meetingFolder=f"https://www.3gpp.org/ftp/tsg_ran/WG1_RL1/{slug.upper()}/"
        ),
        lastIngestedAt=_iso(NOW),
    )

    room_objs = [
        Room(
            roomId=f"{slug}-room-{i + 1}",
            meetingId=meeting.id,
            roomName=rn,
            order=i,
            floor=floor,
        )
        for i, (rn, floor) in enumerate(rooms)
    ]

    sources = [
        ScheduleSource(
            sourceId=f"{slug}-src-{i + 1}",
            meetingId=meeting.id,
            fileName=fn,
            label=fn.rsplit(".", 1)[0][:38],
            type=t,  # type: ignore[arg-type]
            origin="public",
            retrievedAt=_iso(NOW),
            revision=rev,
            revisionParts=parts,
            url=f"{meeting.sources.meetingFolder}Inbox/{fn}" if meeting.sources else None,
            contentHash=hashlib.sha256(fn.encode()).hexdigest(),
            confidence=conf,
        )
        for i, (fn, t, rev, parts, conf) in enumerate(doc_names)
    ]

    agenda_items = [
        AgendaItem(code=code, meetingId=meeting.id, title=title, parent=parent, topicKey=_topic_key(title))
        for code, title, parent in agenda
    ]

    leaves = [a for a in agenda_items if a.parent]
    sessions: list[Session] = []
    slots = [("09:00", "10:30"), ("11:00", "12:30"), ("14:00", "15:30"), ("16:00", "17:30")]
    breaks = [("10:30", "11:00", "Coffee break", "break"), ("12:30", "14:00", "Lunch", "lunch")]

    n = 0
    for d in range(days):
        day_date = start + timedelta(days=d)
        day_name = day_date.strftime("%A")
        for si, (st, et) in enumerate(slots):
            for ri, room in enumerate(room_objs):
                if d == 0 and si == 0 and ri > 0:
                    continue  # opening plenary occupies the main room only
                item = leaves[n % len(leaves)]
                n += 1
                plenary = d == 0 and si == 0
                sessions.append(
                    Session(
                        sessionId=f"{slug}-s{d}-{si}-{ri}",
                        meetingId=meeting.id,
                        date=day_date.isoformat(),
                        day=day_name,
                        startTime=st,
                        endTime=et,
                        roomId=room.roomId,
                        roomName=room.roomName,
                        topic="Opening plenary" if plenary else item.title,
                        topicKey=_topic_key("plenary" if plenary else item.title),
                        agendaItems=[] if plenary else [item.code],
                        mode="offline" if ri % 3 else "hybrid",
                        kind="plenary" if plenary else "session",
                        sources=[SessionSourceRef(sourceId=sources[0].sourceId, contributed=["*"])]
                        + (
                            [SessionSourceRef(sourceId=sources[1].sourceId, contributed=["roomId"])]
                            if len(sources) > 1 and ri == 1
                            else []
                        ),
                    )
                )
        for st, et, label, kind_ in breaks:
            for room in room_objs[:1]:
                sessions.append(
                    Session(
                        sessionId=f"{slug}-{d}-{kind_}",
                        meetingId=meeting.id,
                        date=day_date.isoformat(),
                        day=day_name,
                        startTime=st,
                        endTime=et,
                        roomId=room.roomId,
                        roomName=room.roomName,
                        topic=label,
                        topicKey=kind_,
                        kind=kind_,  # type: ignore[arg-type]
                    )
                )

    changes = [
        ScheduleChange(
            changeId=f"{slug}-c1",
            meetingId=meeting.id,
            detectedAt=_iso(NOW - timedelta(hours=2)),
            type="room_changed",
            title=f"{sessions[1].topic} moved room",
            detail="A newer revision of the schedule places this session in a different room.",
            agendaItems=sessions[1].agendaItems,
            sessionId=sessions[1].sessionId,
            from_=room_objs[0].roomName,
            to=sessions[1].roomName,
            sourceIds=[sources[0].sourceId],
        ),
        ScheduleChange(
            changeId=f"{slug}-c2",
            meetingId=meeting.id,
            detectedAt=_iso(NOW - timedelta(hours=6)),
            type="start_time_changed",
            title=f"{sessions[2].topic} starts later",
            detail="Start time shifted after the previous session was extended.",
            agendaItems=sessions[2].agendaItems,
            sessionId=sessions[2].sessionId,
            from_="13:30",
            to=sessions[2].startTime,
            sourceIds=[s.sourceId for s in sources[:2]],
        ),
    ]

    return ScheduleBundle(
        generatedAt=_iso(NOW),
        meeting=meeting,
        rooms=room_objs,
        sessions=sessions,
        agendaItems=agenda_items,
        sources=sources,
        changes=changes,
        conflicts=[],
        ingest=IngestStatus(state="ok", lastSuccessfulAt=_iso(NOW), lastAttemptAt=_iso(NOW)),
    )


def fixture_meetings() -> list[ScheduleBundle]:
    today = datetime.now(timezone.utc).date()

    real = build_meeting(
        slug="ran1-126",
        name="RAN1#126",
        kind="regular",
        number=126,
        start=date(2026, 8, 17),
        days=5,
        tz="Europe/Prague",
        city="Prague",
        country="Czechia",
        venue="Prague Congress Centre",
        rooms=[
            ("Forum Hall", "Level 2"),
            ("Congress Hall", "Level 2"),
            ("Meeting Room 221", "Level 2"),
            ("Meeting Room 243", "Level 2"),
            ("Club E", "Level 1"),
        ],
        agenda=[
            ("9", "General", None),
            ("9.1", "Maintenance of Rel-18", "9"),
            ("9.2", "Maintenance of Rel-19", "9"),
            ("10", "Release 20 study items", None),
            ("10.1", "AI/ML for air interface", "10"),
            ("10.2", "Integrated sensing and communication", "10"),
            ("10.3", "Ambient IoT", "10"),
            ("10.4", "MIMO evolution", "10"),
            ("10.5", "Non-terrestrial networks", "10"),
        ],
        doc_names=[
            ("RAN1-126_agenda_and_schedule_v07.docx", "main_schedule", "v07", [7], 0.96),
            ("RAN1-126_online_and_offline_sessions_v03.docx", "online_schedule", "v03", [3], 0.9),
            ("RAN1-126_sub-chair_detailed_schedule_v02_1.docx", "subchair_schedule", "v02.1", [2, 1], 0.74),
            ("RAN1-126_venue_information.docx", "venue_information", None, [], 1.0),
        ],
    )

    # Deliberately different in every dimension, and always in the future so
    # both statuses are exercised.
    synthetic_start = today + timedelta(days=45 - today.weekday())
    synthetic = build_meeting(
        slug="ran1-131-bis",
        name="RAN1#131-bis",
        kind="bis",
        number=131,
        start=synthetic_start,
        days=3,
        tz="Asia/Seoul",
        city="Incheon",
        country="Korea",
        venue="Songdo Convensia",
        rooms=[
            ("Premier Ballroom", "3F"),
            ("Grand Ballroom A", "3F"),
            ("Room 301", "3F"),
        ],
        agenda=[
            ("7", "Ad-hoc topics", None),
            ("7.1", "Waveform enhancements", "7"),
            ("7.2", "Positioning accuracy", "7"),
            ("8", "Cross-release maintenance", None),
            ("8.1", "Corrections and clarifications", "8"),
        ],
        doc_names=[
            ("RAN1-131bis_draft_schedule_v02.docx", "main_schedule", "v02", [2], 0.88),
            ("RAN1-131bis_room_allocation_v01.docx", "room_schedule", "v01", [1], 0.81),
        ],
    )

    return [real, synthetic]
