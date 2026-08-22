"""Normalized data model shared by the whole ingestion pipeline.

These dataclasses mirror src/types/meeting.ts and src/types/schedule.ts one to
one. Nothing here is specific to a single meeting: every record carries the
meeting id it belongs to, so the same code publishes RAN1#126, RAN1#131-bis or
any future ad-hoc meeting without modification.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal

SCHEMA_VERSION = 2

MeetingType = Literal["regular", "bis", "adhoc", "other"]
MeetingStatus = Literal["upcoming", "active", "completed"]
SourceType = Literal[
    "main_schedule",
    "chair_schedule",
    "subchair_schedule",
    "online_schedule",
    "offline_schedule",
    "room_schedule",
    "detailed_schedule",
    "venue_information",
    "unknown_schedule",
]
SourceOrigin = Literal["public", "meeting-local", "manual"]
SessionKind = Literal["session", "break", "lunch", "plenary", "social"]
SessionStatus = Literal["scheduled", "moved", "cancelled", "tentative"]


def _clean(data: dict[str, Any]) -> dict[str, Any]:
    """Drop None values so the published JSON stays small and optional-safe."""
    return {k: v for k, v in data.items() if v is not None}


@dataclass
class MeetingSourceFolders:
    meetingFolder: str | None = None
    inbox: str | None = None
    chairNotes: str | None = None
    agenda: str | None = None


@dataclass
class Meeting:
    id: str
    slug: str
    name: str
    type: MeetingType
    startDate: str
    endDate: str
    timezone: str
    status: MeetingStatus = "upcoming"
    meetingNumber: int | None = None
    venue: str | None = None
    city: str | None = None
    country: str | None = None
    schedulePublished: bool = False
    statusOverride: str | None = None
    sources: MeetingSourceFolders | None = None
    floorplanUrl: str | None = None
    lastIngestedAt: str | None = None

    def to_json(self) -> dict[str, Any]:
        data = _clean(asdict(self))
        if self.sources is not None:
            data["sources"] = _clean(asdict(self.sources))
        return data


@dataclass
class Room:
    roomId: str
    meetingId: str
    roomName: str
    order: int
    shortName: str | None = None
    floor: str | None = None
    description: str | None = None

    def to_json(self) -> dict[str, Any]:
        return _clean(asdict(self))


@dataclass
class ScheduleSource:
    sourceId: str
    meetingId: str
    fileName: str
    label: str
    type: SourceType
    origin: SourceOrigin
    retrievedAt: str
    revision: str | None = None
    revisionParts: list[int] | None = None
    url: str | None = None
    contentHash: str | None = None
    modifiedAt: str | None = None
    confidence: float | None = None

    def to_json(self) -> dict[str, Any]:
        return _clean(asdict(self))


@dataclass
class SessionSourceRef:
    sourceId: str
    contributed: list[str] = field(default_factory=list)


@dataclass
class AgendaSlot:
    """One agenda item inside a session block, with its own share of the time."""

    code: str | None
    label: str
    minutes: int | None = None
    startTime: str | None = None
    endTime: str | None = None

    def to_json(self) -> dict[str, Any]:
        return _clean(asdict(self))


@dataclass
class Session:
    sessionId: str
    meetingId: str
    date: str
    day: str
    startTime: str
    endTime: str
    roomId: str
    roomName: str
    topic: str
    topicKey: str
    agendaItems: list[str] = field(default_factory=list)
    agendaBreakdown: list[AgendaSlot] = field(default_factory=list)
    sessionLead: str | None = None
    group: str | None = None
    mode: str | None = None
    kind: SessionKind = "session"
    status: SessionStatus = "scheduled"
    note: str | None = None
    sources: list[SessionSourceRef] = field(default_factory=list)

    @property
    def slot_key(self) -> str:
        """Stable per-time-slot key used for incremental merging."""
        return f"{self.date}|{self.startTime}|{self.endTime}|{self.roomId}"

    def to_json(self) -> dict[str, Any]:
        return _clean(asdict(self))


@dataclass
class AgendaItem:
    code: str
    meetingId: str
    title: str
    parent: str | None = None
    topicKey: str | None = None

    def to_json(self) -> dict[str, Any]:
        return _clean(asdict(self))


@dataclass
class ScheduleChange:
    changeId: str
    meetingId: str
    detectedAt: str
    type: str
    title: str
    detail: str
    agendaItems: list[str] = field(default_factory=list)
    sessionId: str | None = None
    from_: str | None = None
    to: str | None = None
    sourceIds: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["from"] = data.pop("from_")
        return _clean(data)


@dataclass
class ScheduleConflict:
    conflictId: str
    meetingId: str
    sessionId: str
    field: str
    values: list[dict[str, str]]
    resolved: bool = False

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IngestStatus:
    state: str
    lastSuccessfulAt: str
    lastAttemptAt: str | None = None
    message: str | None = None

    def to_json(self) -> dict[str, Any]:
        return _clean(asdict(self))


@dataclass
class ScheduleBundle:
    generatedAt: str
    meeting: Meeting
    rooms: list[Room] = field(default_factory=list)
    sessions: list[Session] = field(default_factory=list)
    agendaItems: list[AgendaItem] = field(default_factory=list)
    sources: list[ScheduleSource] = field(default_factory=list)
    changes: list[ScheduleChange] = field(default_factory=list)
    conflicts: list[ScheduleConflict] = field(default_factory=list)
    ingest: IngestStatus | None = None
    schemaVersion: int = SCHEMA_VERSION

    def to_json(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schemaVersion,
            "generatedAt": self.generatedAt,
            "meeting": self.meeting.to_json(),
            "rooms": [r.to_json() for r in self.rooms],
            "sessions": [s.to_json() for s in self.sessions],
            "agendaItems": [a.to_json() for a in self.agendaItems],
            "sources": [s.to_json() for s in self.sources],
            "changes": [c.to_json() for c in self.changes],
            "conflicts": [c.to_json() for c in self.conflicts],
            "ingest": (self.ingest or IngestStatus("ok", self.generatedAt)).to_json(),
        }
