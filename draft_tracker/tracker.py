"""Draft Tracker orchestration.

Scan a meeting's drafts tree through any `DraftSource`, map folders onto the
canonical agenda, match artifacts across sources, and emit normalized events.

Deliberately separate from the schedule ingestion pipeline: schedule parsing
(chair DOCX) and draft watching (Inbox/drafts tree) are two subsystems that
only meet at the canonical meeting and agenda-item objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .agenda_mapper import AgendaMapper, AgendaMapping, is_round_folder
from .artifact_matcher import (
    artifact_fingerprint,
    content_changed,
    find_existing,
    merge_source,
    normalize_path,
    now_iso,
    record_revision,
    sha256,
    stable_id,
)
from .directory_parser import NormalizedDirectoryEntry
from .event_detector import (
    new_file_event,
    new_folder_event,
    removed_file_event,
    updated_file_event,
)
from .fl_classifier import classify
from .models import (
    DraftArtifact,
    DraftArtifactSource,
    DraftEvent,
    DraftFolder,
    DraftIndex,
)

MAX_EVENTS = 500
MAX_DEPTH = 6


@dataclass
class ScanConfig:
    """How aggressive a scan may be with the source server."""

    hash_files: bool = False
    """Download bytes to fingerprint content. Only worth it for FL summaries."""
    hash_only_fl: bool = True
    max_folders: int = 400


def _rehydrate(previous: dict[str, Any] | None) -> tuple[
    dict[str, DraftFolder], dict[str, DraftArtifact], list[DraftEvent], bool, str | None
]:
    if not previous:
        return {}, {}, [], False, None
    folders = {f["id"]: DraftFolder(**f) for f in previous.get("folders", [])}
    artifacts: dict[str, DraftArtifact] = {}
    for raw in previous.get("artifacts", []):
        data = dict(raw)
        data["sources"] = [DraftArtifactSource(**s) for s in data.get("sources", [])]
        artifacts[data["id"]] = DraftArtifact(**data)
    events = [DraftEvent(**e) for e in previous.get("events", [])]
    return folders, artifacts, events, bool(previous.get("baselinedAt")), previous.get("baselinedAt")


def scan_meeting(
    *,
    meeting_id: str,
    source: Any,
    agenda_codes: dict[str, str],
    previous: dict[str, Any] | None = None,
    monitoring: bool = True,
    config: ScanConfig | None = None,
) -> DraftIndex:
    """One stateful scan pass. Never raises for an unreachable source."""
    config = config or ScanConfig()
    detected_at = now_iso()
    mapper = AgendaMapper(agenda_codes)
    folders, artifacts, events, has_baseline, baselined_at = _rehydrate(previous)
    baseline_scan = not has_baseline

    root = source.discover_drafts_root()
    if not root:
        # Nothing published yet, or the source is unreachable: keep prior state.
        return DraftIndex(
            meetingId=meeting_id,
            generatedAt=detected_at,
            scanState="delayed" if previous else "inactive",
            lastSuccessfulScanAt=(previous or {}).get("lastSuccessfulScanAt"),
            baselinedAt=baselined_at,
            monitoring=monitoring,
            draftsRootUrl=(previous or {}).get("draftsRootUrl"),
            folders=list(folders.values()),
            artifacts=list(artifacts.values()),
            events=events[:MAX_EVENTS],
            unmappedFolders=(previous or {}).get("unmappedFolders", []),
            message="No drafts folder published for this meeting yet."
            if not previous
            else "Draft activity update delayed; showing last successful scan.",
        )

    source_type = getattr(source, "source_type", "public")
    seen_folder_ids: set[str] = set()
    seen_artifact_ids: set[str] = set()
    new_events: list[DraftEvent] = []
    unmapped: list[str] = []
    by_hash = {a.contentHash: a.id for a in artifacts.values() if a.contentHash}
    visited = 0

    def walk(
        url: str,
        path_parts: list[str],
        parent_folder: DraftFolder | None,
        parent_mapping: AgendaMapping | None,
        depth: int,
    ) -> None:
        nonlocal visited
        if depth > MAX_DEPTH or visited > config.max_folders:
            return
        visited += 1
        entries: Iterable[NormalizedDirectoryEntry] = source.list_directory(url)
        files = [e for e in entries if not e.is_dir]

        if parent_folder:
            parent_folder.fileCount = len(files)

        for entry in entries:
            if entry.is_dir:
                parts = [*path_parts, entry.name]
                mapping = mapper.map_folder(entry.name, parent_mapping)
                folder_id = stable_id("fld", meeting_id, normalize_path(parts))
                existing = folders.get(folder_id)
                if existing is None:
                    folder = DraftFolder(
                        id=folder_id,
                        meetingId=meeting_id,
                        name=entry.name,
                        normalizedPath=normalize_path(parts),
                        sourceType=source_type,
                        firstSeenAt=detected_at,
                        lastSeenAt=detected_at,
                        agendaItemId=mapping.agenda_item_id,
                        agendaConfidence=mapping.confidence,
                        agendaMethod=mapping.method,
                        parentFolderId=parent_folder.id if parent_folder else None,
                        roundNumber=is_round_folder(entry.name),
                        depth=depth,
                        url=entry.url,
                    )
                    folders[folder_id] = folder
                    if not baseline_scan:
                        new_events.append(
                            new_folder_event(meeting_id, folder, detected_at, source_type)
                        )
                else:
                    folder = existing
                    folder.lastSeenAt = detected_at
                    folder.agendaItemId = mapping.agenda_item_id or folder.agendaItemId
                    folder.agendaConfidence = mapping.confidence
                    folder.agendaMethod = mapping.method
                    folder.url = entry.url
                seen_folder_ids.add(folder_id)
                if mapping.unmapped:
                    unmapped.append(folder.normalizedPath)
                walk(entry.url, parts, folder, mapping, depth + 1)

        if parent_folder is None:
            return

        for entry in files:
            _ingest_file(
                entry,
                folder=parent_folder,
                path_parts=path_parts,
                mapping=parent_mapping,
            )

    def _ingest_file(
        entry: NormalizedDirectoryEntry,
        *,
        folder: DraftFolder,
        path_parts: list[str],
        mapping: AgendaMapping | None,
    ) -> None:
        classification = classify(entry.name, path_parts)
        folder_path = normalize_path(path_parts)
        fingerprint = artifact_fingerprint(meeting_id, folder_path, entry.name)

        content_hash: str | None = None
        if config.hash_files and (
            not config.hash_only_fl or classification.file_type == "fl_summary"
        ):
            data = source.fetch_bytes(entry.url)
            if data:
                content_hash = sha256(data)

        existing = find_existing(
            artifacts, by_hash, fingerprint=fingerprint, content_hash=content_hash
        )
        appearance = DraftArtifactSource(
            sourceType=source_type,
            sourcePath=f"{folder_path}/{entry.name}".strip("/"),
            url=entry.url,
            firstSeenAt=detected_at,
            lastSeenAt=detected_at,
            size=entry.size,
            modifiedAt=entry.modified_at,
        )

        if existing is None:
            artifact = DraftArtifact(
                id=fingerprint,
                meetingId=meeting_id,
                folderId=folder.id,
                filename=entry.name,
                normalizedPath=appearance.sourcePath,
                fileType=classification.file_type,
                classificationConfidence=classification.confidence,
                documentKey=classification.document_key,
                firstSeenAt=detected_at,
                lastSeenAt=detected_at,
                agendaItemId=mapping.agenda_item_id if mapping else None,
                revision=classification.revision,
                contentHash=content_hash,
                size=entry.size,
                modifiedAt=entry.modified_at,
                sources=[appearance],
            )
            record_revision(artifact, detected_at)
            artifacts[artifact.id] = artifact
            if content_hash:
                by_hash[content_hash] = artifact.id
            seen_artifact_ids.add(artifact.id)
            if not baseline_scan:
                new_events.append(new_file_event(meeting_id, artifact, detected_at, source_type))
            return

        # Known artifact: a second source appearance is a sync, not an upload.
        existing.lastSeenAt = detected_at
        existing.removedAt = None
        existing.agendaItemId = (mapping.agenda_item_id if mapping else None) or existing.agendaItemId
        merge_source(existing, appearance)
        seen_artifact_ids.add(existing.id)

        if content_changed(
            existing, content_hash=content_hash, size=entry.size, modified_at=entry.modified_at
        ):
            existing.contentHash = content_hash or existing.contentHash
            existing.size = entry.size
            existing.modifiedAt = entry.modified_at
            record_revision(existing, detected_at)
            if content_hash:
                by_hash[content_hash] = existing.id
            if not baseline_scan:
                new_events.append(
                    updated_file_event(meeting_id, existing, detected_at, source_type)
                )
        else:
            if content_hash and not existing.contentHash:
                existing.contentHash = content_hash
                by_hash[content_hash] = existing.id
            existing.size = existing.size or entry.size
            existing.modifiedAt = existing.modifiedAt or entry.modified_at

    root_folder = DraftFolder(
        id=stable_id("fld", meeting_id, "drafts"),
        meetingId=meeting_id,
        name="drafts",
        normalizedPath="",
        sourceType=source_type,
        firstSeenAt=detected_at,
        lastSeenAt=detected_at,
        depth=0,
        url=root,
    )
    folders.setdefault(root_folder.id, root_folder)
    seen_folder_ids.add(root_folder.id)
    walk(root, [], root_folder, None, 1)

    # Removals only count for the source we just scanned successfully.
    for artifact in artifacts.values():
        if (
            artifact.id not in seen_artifact_ids
            and artifact.removedAt is None
            and source_type in artifact.source_types
            and len(artifact.source_types) == 1
        ):
            artifact.removedAt = detected_at
            if not baseline_scan:
                new_events.append(
                    removed_file_event(meeting_id, artifact, detected_at, source_type)
                )

    merged_events = new_events + events
    return DraftIndex(
        meetingId=meeting_id,
        generatedAt=detected_at,
        scanState="baseline" if baseline_scan else "ok",
        lastSuccessfulScanAt=detected_at,
        baselinedAt=baselined_at or detected_at,
        monitoring=monitoring,
        draftsRootUrl=root,
        folders=sorted(folders.values(), key=lambda f: f.normalizedPath),
        artifacts=sorted(artifacts.values(), key=lambda a: a.normalizedPath),
        events=merged_events[:MAX_EVENTS],
        newEventIds=[e.id for e in new_events],
        unmappedFolders=sorted(set(unmapped)),
        message=None,
    )
