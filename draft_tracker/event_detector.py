"""Turn two directory snapshots into normalized draft events.

Rules that matter:
  * Events state a *filesystem fact* first (NEW_FILE, NEW_FOLDER, ...).
    Meaning ("this is a discussion round", "this is an FL summary") is an
    optional `semanticType` added only when classification is confident.
  * The first scan of a meeting is a BASELINE: existing files become known
    state and generate no events (nobody wants "137 new files" when the
    tracker starts, or after a meeting rollover).
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
    semantic: str | None = None,
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
        semanticType=semantic,  # type: ignore[arg-type]
        agendaItemId=agenda,
        artifactId=artifact.id if artifact else None,
        folderId=folder.id if folder else (artifact.folderId if artifact else None),
        title=title,
        detail=detail,
        fileType=artifact.fileType if artifact else None,
        folderPath=folder.normalizedPath
        if folder
        else (artifact.folderPath if artifact else None),
        roundNumber=round_number,
        url=url,
    )


def new_folder_event(
    meeting_id: str, folder: DraftFolder, detected_at: str, source_type: str
) -> DraftEvent:
    """Always NEW_FOLDER. "Round" is a label, never a separate kind of event."""
    if folder.folderType == "round" and folder.roundNumber is not None:
        semantic, title = "NEW_ROUND", f"New round: {folder.name}"
    elif folder.folderType == "fl":
        semantic, title = "NEW_FL_FOLDER", f"New FL folder: {folder.name}"
    else:
        semantic, title = None, f"New draft folder: {folder.name}"
    return _event(
        meeting_id,
        "NEW_FOLDER",
        detected_at,
        source_type=source_type,
        agenda=folder.agendaItemId,
        title=title,
        detail=folder.normalizedPath,
        semantic=semantic,
        folder=folder,
        round_number=folder.roundNumber,
        url=folder.url,
    )


def removed_folder_event(
    meeting_id: str, folder: DraftFolder, detected_at: str, source_type: str
) -> DraftEvent:
    """A folder that disappeared. Never guessed to be a rename (see §21)."""
    return _event(
        meeting_id,
        "FOLDER_REMOVED",
        detected_at,
        source_type=source_type,
        agenda=folder.agendaItemId,
        title=f"Folder removed: {folder.name}",
        detail=folder.normalizedPath,
        folder=folder,
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
        semantic="FL_SUMMARY_UPDATED" if is_fl else None,
        artifact=artifact,
        url=artifact.sources[0].url if artifact.sources else None,
    )


def updated_file_event(
    meeting_id: str, artifact: DraftArtifact, detected_at: str, source_type: str
) -> DraftEvent:
    is_fl = artifact.fileType == "fl_summary"
    return _event(
        meeting_id,
        "FILE_UPDATED",
        detected_at,
        source_type=source_type,
        agenda=artifact.agendaItemId,
        title=("FL summary updated" if is_fl else "Draft updated") + f": {artifact.filename}",
        detail=artifact.normalizedPath,
        semantic="FL_SUMMARY_UPDATED" if is_fl else None,
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


def group_new_folder_events(events: list[DraftEvent]) -> list[DraftEvent]:
    """Tag file events that arrived inside a brand-new folder (§14).

    Every individual event is still stored; the shared `groupKey` lets the UI
    show "New folder: Round 2 - 3 files added" instead of four separate pings.
    """
    new_folders = {
        e.folderId: e for e in events if e.eventType == "NEW_FOLDER" and e.folderId
    }
    if not new_folders:
        return events
    for event in events:
        if event.eventType == "NEW_FILE" and event.folderId in new_folders:
            event.groupKey = new_folders[event.folderId].id
    for event in new_folders.values():
        event.groupKey = event.id
    return events
