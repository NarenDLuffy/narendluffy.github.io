"""Turn two directory snapshots into normalized draft events.

Rules that matter:
  * The first scan of a meeting is a BASELINE: existing files become known
    state and generate no events (nobody wants "137 new files" when the
    tracker starts, or after a meeting rollover).
  * Events are derived from the normalized artifact model, never from raw
    directory timestamps.
  * A known artifact appearing on an additional source is a synchronization,
    not a new upload.
"""

from __future__ import annotations

from .artifact_matcher import stable_id
from .models import DraftArtifact, DraftEvent, DraftFolder


def _event(
    meeting_id: str,
    event_type: str,
    detected_at: str,
    *,
    source_type: str,
    agenda: str | None,
    title: str,
    detail: str | None = None,
    artifact: DraftArtifact | None = None,
    folder: DraftFolder | None = None,
    round_number: int | None = None,
    url: str | None = None,
) -> DraftEvent:
    key = artifact.id if artifact else (folder.id if folder else title)
    return DraftEvent(
        id=stable_id("evt", meeting_id, event_type, key, detected_at),
        meetingId=meeting_id,
        eventType=event_type,  # type: ignore[arg-type]
        detectedAt=detected_at,
        sourceType=source_type,  # type: ignore[arg-type]
        agendaItemId=agenda,
        artifactId=artifact.id if artifact else None,
        folderId=folder.id if folder else (artifact.folderId if artifact else None),
        title=title,
        detail=detail,
        fileType=artifact.fileType if artifact else None,
        folderPath=folder.normalizedPath if folder else (artifact.normalizedPath if artifact else None),
        roundNumber=round_number,
        url=url,
    )


def new_folder_event(
    meeting_id: str, folder: DraftFolder, detected_at: str, source_type: str
) -> DraftEvent:
    if folder.roundNumber is not None:
        return _event(
            meeting_id,
            "NEW_ROUND",
            detected_at,
            source_type=source_type,
            agenda=folder.agendaItemId,
            title=f"{folder.name} created",
            detail=folder.normalizedPath,
            folder=folder,
            round_number=folder.roundNumber,
            url=folder.url,
        )
    return _event(
        meeting_id,
        "NEW_FOLDER",
        detected_at,
        source_type=source_type,
        agenda=folder.agendaItemId,
        title=f"New folder {folder.name}",
        detail=folder.normalizedPath,
        folder=folder,
        url=folder.url,
    )


def new_file_event(
    meeting_id: str, artifact: DraftArtifact, detected_at: str, source_type: str
) -> DraftEvent:
    is_fl = artifact.fileType == "fl_summary"
    return _event(
        meeting_id,
        "NEW_FILE",
        detected_at,
        source_type=source_type,
        agenda=artifact.agendaItemId,
        title=("New FL summary" if is_fl else "New draft") + f": {artifact.filename}",
        detail=artifact.normalizedPath,
        artifact=artifact,
        url=artifact.sources[0].url if artifact.sources else None,
    )


def updated_file_event(
    meeting_id: str, artifact: DraftArtifact, detected_at: str, source_type: str
) -> DraftEvent:
    is_fl = artifact.fileType == "fl_summary"
    return _event(
        meeting_id,
        "FL_SUMMARY_UPDATED" if is_fl else "FILE_UPDATED",
        detected_at,
        source_type=source_type,
        agenda=artifact.agendaItemId,
        title=("FL summary updated" if is_fl else "Draft updated") + f": {artifact.filename}",
        detail=artifact.normalizedPath,
        artifact=artifact,
        url=artifact.sources[0].url if artifact.sources else None,
    )


def removed_file_event(
    meeting_id: str, artifact: DraftArtifact, detected_at: str, source_type: str
) -> DraftEvent:
    return _event(
        meeting_id,
        "FILE_REMOVED",
        detected_at,
        source_type=source_type,
        agenda=artifact.agendaItemId,
        title=f"Removed: {artifact.filename}",
        detail=artifact.normalizedPath,
        artifact=artifact,
    )
