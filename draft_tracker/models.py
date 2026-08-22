"""Normalized draft-tracking model, independent of any FTP layout.

Published as `public/data/meetings/<slug>/drafts.json`; the TypeScript mirror
lives in `src/types/drafts.ts`.

Two principles shape this model:

1. *Filesystem fact is separated from semantic interpretation.* Events describe
   what happened on the server (NEW_FILE, NEW_FOLDER, ...); an optional
   `semanticType` adds meaning (NEW_ROUND, FL_SUMMARY_UPDATED) only when the
   classifier is confident. Nothing downstream may require the semantics.
2. A *logical artifact* (one uploaded document) is modelled separately from the
   *source appearances* of that artifact, so the same file arriving first on the
   meeting-local server and later on the public 3GPP site is one artifact with
   two appearances - and therefore one notification, never two.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

DRAFTS_SCHEMA_VERSION = 2

SourceType = Literal["public", "meeting-local"]

# Filesystem facts only. No RAN1 vocabulary here, ever.
EventType = Literal[
    "NEW_FILE",
    "FILE_UPDATED",
    "NEW_FOLDER",
    "FILE_REMOVED",
    "FOLDER_REMOVED",
]

# Optional interpretation layered on top of a filesystem fact.
SemanticType = Literal["NEW_ROUND", "NEW_FL_FOLDER", "FL_SUMMARY_UPDATED", "OTHER"]

# agenda | round | fl | topic | generic | unknown
FolderType = str


@dataclass
class DraftFolder:
    id: str
    meetingId: str
    name: str
    normalizedPath: str
    sourceType: SourceType
    firstSeenAt: str
    lastSeenAt: str
    agendaItemId: str | None = None
    agendaConfidence: float = 0.0
    agendaMethod: str = "unmapped"
    parentFolderId: str | None = None
    parentPath: str | None = None
    depth: int = 0
    folderType: FolderType = "generic"
    classificationConfidence: float = 0.0
    roundNumber: int | None = None
    url: str | None = None
    """Files directly inside this folder."""
    fileCount: int = 0
    """Files anywhere below this folder, including itself."""
    subtreeFileCount: int = 0
    removedAt: str | None = None


@dataclass
class DraftArtifactSource:
    sourceType: SourceType
    sourcePath: str
    url: str | None
    firstSeenAt: str
    lastSeenAt: str
    size: int | None = None
    modifiedAt: str | None = None


@dataclass
class DraftArtifact:
    id: str
    meetingId: str
    folderId: str
    filename: str
    normalizedPath: str
    fileType: str
    classificationConfidence: float
    documentKey: str
    firstSeenAt: str
    lastSeenAt: str
    agendaItemId: str | None = None
    """Folder path segments between the agenda folder and the file."""
    folderPath: str | None = None
    depth: int = 0
    revision: int | None = None
    contentHash: str | None = None
    size: int | None = None
    modifiedAt: str | None = None
    sources: list[DraftArtifactSource] = field(default_factory=list)
    revisions: list[dict[str, Any]] = field(default_factory=list)
    removedAt: str | None = None

    @property
    def source_types(self) -> set[str]:
        return {s.sourceType for s in self.sources}


@dataclass
class DraftEvent:
    id: str
    meetingId: str
    eventType: EventType
    detectedAt: str
    sourceType: SourceType
    semanticType: SemanticType | None = None
    agendaItemId: str | None = None
    artifactId: str | None = None
    folderId: str | None = None
    title: str = ""
    detail: str | None = None
    fileType: str | None = None
    folderPath: str | None = None
    roundNumber: int | None = None
    url: str | None = None
    """Set when this event is folded into a folder-level group notification."""
    groupKey: str | None = None


@dataclass
class DraftIndex:
    meetingId: str
    generatedAt: str
    scanState: str = "ok"  # ok | delayed | baseline | inactive
    lastSuccessfulScanAt: str | None = None
    baselinedAt: str | None = None
    monitoring: bool = True
    draftsRootUrl: str | None = None
    folders: list[DraftFolder] = field(default_factory=list)
    artifacts: list[DraftArtifact] = field(default_factory=list)
    events: list[DraftEvent] = field(default_factory=list)
    """IDs of events created by the latest scan (freshness is never inferred
    from timestamps, which can collide within one second)."""
    newEventIds: list[str] = field(default_factory=list)
    unmappedFolders: list[str] = field(default_factory=list)
    message: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "schemaVersion": DRAFTS_SCHEMA_VERSION,
            **asdict(self),
        }
