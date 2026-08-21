"""Normalized schedule data model shared by the whole ingestion pipeline.

These dataclasses mirror src/types/schedule.ts one-to-one. The frontend never
sees DOCX structure: the only contract between Python and React is the JSON
emitted from these models.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal

SCHEMA_VERSION = 1

SourceRole = Literal["main", "detail"]
SessionKind = Literal["session", "break", "lunch", "plenary", "social"]
SessionStatus = Literal["scheduled", "moved", "cancelled", "tentative"]


@dataclass
class Meeting:
    meetingId: str
    meetingName: str
    startDate: str
    endDate: str
    venue: str
    city: str
    timezone: str
    status: str = "upcoming"


@dataclass
class Room:
    roomId: str
    roomName: str
    order: int
    area: str | None = None


@dataclass
class ScheduleSource:
    sourceId: str
    fileName: str
    label: str
    role: SourceRole
    retrievedAt: str
    owner: str | None = None
    url: str | None = None
    version: str | None = None
    # sha256 of the downloaded document; drives incremental parsing
    contentHash: str | None = None


@dataclass
class SessionSourceRef:
    sourceId: str
    contributed: list[str] = field(default_factory=list)


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
    sessionLead: str | None = None
    mode: str | None = None
    kind: SessionKind = "session"
    status: SessionStatus = "scheduled"
    note: str | None = None
    sources: list[SessionSourceRef] = field(default_factory=list)

    @property
    def slot_key(self) -> str:
        """Stable per-time-slot key used for incremental merging/caching."""
        return f"{self.date}|{self.startTime}|{self.endTime}|{self.roomId}"


@dataclass
class AgendaItem:
    code: str
    title: str
    parent: str | None = None
    topicKey: str | None = None


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
        return data


@dataclass
class ScheduleConflict:
    conflictId: str
    sessionId: str
    field: str
    values: list[dict[str, str]]
    resolved: bool = False


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
    schemaVersion: int = SCHEMA_VERSION

    def to_json(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schemaVersion,
            "generatedAt": self.generatedAt,
            "meeting": asdict(self.meeting),
            "rooms": [asdict(r) for r in self.rooms],
            "sessions": [asdict(s) for s in self.sessions],
            "agendaItems": [asdict(a) for a in self.agendaItems],
            "sources": [asdict(s) for s in self.sources],
            "changes": [c.to_json() for c in self.changes],
            "conflicts": [asdict(c) for c in self.conflicts],
        }
