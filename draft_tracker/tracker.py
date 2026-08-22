"""Draft Tracker orchestration.

Processing order is deliberate and never inverted:

    discover raw entries -> build the complete tree -> normalize paths
      -> identify agenda folders -> propagate agenda to descendants
      -> optionally classify folder types -> classify FL summaries
      -> diff against the previous snapshot -> emit events

The tracker therefore adapts to whatever the chairs and feature leads create on
the server. There is no expected template: rounds, custom folder names, files
sitting directly in an agenda folder and arbitrarily deep nesting are all just
data. Folder names are never application configuration.

Deliberately separate from the schedule ingestion pipeline: schedule parsing
(chair DOCX) and draft watching (Inbox/drafts tree) are two subsystems that
only meet at the canonical meeting and agenda-item objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .agenda_mapper import AgendaMapper, AgendaMapping, extract_code
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
from .directory_tree import SAFETY_MAX_DEPTH, SAFETY_MAX_NODES, TreeNode, build_tree
from .event_detector import (
    group_new_folder_events,
    new_file_event,
    new_folder_event,
    removed_file_event,
    removed_folder_event,
    updated_file_event,
)
from .fl_classifier import classify
from .folder_classifier import classify_folder
from .models import (
    DraftArtifact,
    DraftArtifactSource,
    DraftEvent,
    DraftFolder,
    DraftIndex,
)

MAX_EVENTS = 500


@dataclass
class ScanConfig:
    """How aggressive a scan may be with the source server."""

    hash_files: bool = False
    """Download bytes to fingerprint content. Only worth it for FL summaries."""
    hash_only_fl: bool = True
    """Runaway guards only - never an assumption about the real structure."""
    max_folders: int = SAFETY_MAX_NODES
    max_depth: int = SAFETY_MAX_DEPTH


def _rehydrate(previous: dict[str, Any] | None) -> tuple[
    dict[str, DraftFolder], dict[str, DraftArtifact], list[DraftEvent], bool, str | None
]:
    if not previous:
        return {}, {}, [], False, None
    folders: dict[str, DraftFolder] = {}
    known_folder_fields = set(DraftFolder.__dataclass_fields__)
    for raw in previous.get("folders", []):
        folders[raw["id"]] = DraftFolder(
            **{k: v for k, v in raw.items() if k in known_folder_fields}
        )
    artifacts: dict[str, DraftArtifact] = {}
    known_artifact_fields = set(DraftArtifact.__dataclass_fields__)
    for raw in previous.get("artifacts", []):
        data = {k: v for k, v in raw.items() if k in known_artifact_fields}
        data["sources"] = [DraftArtifactSource(**s) for s in raw.get("sources", [])]
        artifacts[data["id"]] = DraftArtifact(**data)
    known_event_fields = set(DraftEvent.__dataclass_fields__)
    # Schema v1 stored NEW_ROUND / FL_SUMMARY_UPDATED as event *types*; they are
    # semantics now, so old rows are migrated rather than dropped.
    legacy = {"NEW_ROUND": ("NEW_FOLDER", "NEW_ROUND"), "FL_SUMMARY_UPDATED": ("FILE_UPDATED", "FL_SUMMARY_UPDATED")}
    events = []
    for raw in previous.get("events", []):
        data = {k: v for k, v in raw.items() if k in known_event_fields}
        migrated = legacy.get(data.get("eventType", ""))
        if migrated:
            data["eventType"], data["semanticType"] = migrated
        events.append(DraftEvent(**data))
    return (
        folders,
        artifacts,
        events,
        bool(previous.get("baselinedAt")),
        previous.get("baselinedAt"),
    )


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

    root_url = source.discover_drafts_root()
    if not root_url:
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

    # --- 1-4: discover everything, build the tree, normalize paths -----------
    tree = build_tree(
        source, root_url, max_depth=config.max_depth, max_nodes=config.max_folders
    )

    seen_folder_ids: set[str] = set()
    seen_artifact_ids: set[str] = set()
    new_events: list[DraftEvent] = []
    unmapped: list[str] = []
    by_hash = {a.contentHash: a.id for a in artifacts.values() if a.contentHash}

    root_folder = DraftFolder(
        id=stable_id("fld", meeting_id, "drafts"),
        meetingId=meeting_id,
        name="drafts",
        normalizedPath="",
        sourceType=source_type,
        firstSeenAt=detected_at,
        lastSeenAt=detected_at,
        depth=0,
        folderType="generic",
        url=root_url,
    )
    existing_root = folders.get(root_folder.id)
    if existing_root:
        existing_root.lastSeenAt = detected_at
        existing_root.url = root_url
        existing_root.removedAt = None
        root_folder = existing_root
    else:
        folders[root_folder.id] = root_folder
    seen_folder_ids.add(root_folder.id)

    folder_by_path: dict[str, DraftFolder] = {"": root_folder}
    mapping_by_path: dict[str, AgendaMapping | None] = {"": None}

    # --- 5-7: agenda identification, propagation, optional classification ----
    for node in tree.walk():
        if node.depth == 0 or not node.is_dir:
            continue
        parent_path = node.parent_path or ""
        parent_folder = folder_by_path.get(parent_path)
        parent_mapping = mapping_by_path.get(parent_path)
        mapping = mapper.map_folder(node.name, parent_mapping)
        mapping_by_path[node.normalized_path] = mapping

        own_code = extract_code(node.name) is not None
        classification = classify_folder(
            node.name,
            has_agenda_code=own_code,
            is_agenda_root=parent_path == "",
        )

        folder_id = stable_id("fld", meeting_id, node.normalized_path)
        existing = folders.get(folder_id)
        if existing is None:
            folder = DraftFolder(
                id=folder_id,
                meetingId=meeting_id,
                name=node.name,
                normalizedPath=node.normalized_path,
                sourceType=source_type,
                firstSeenAt=detected_at,
                lastSeenAt=detected_at,
                agendaItemId=mapping.agenda_item_id,
                agendaConfidence=mapping.confidence,
                agendaMethod=mapping.method,
                parentFolderId=parent_folder.id if parent_folder else None,
                parentPath=parent_path,
                depth=node.depth,
                folderType=classification.folder_type,
                classificationConfidence=classification.confidence,
                roundNumber=classification.round_number,
                url=node.url,
            )
            folders[folder_id] = folder
            if not baseline_scan:
                new_events.append(
                    new_folder_event(meeting_id, folder, detected_at, source_type)
                )
        else:
            folder = existing
            folder.lastSeenAt = detected_at
            folder.removedAt = None
            folder.name = node.name
            folder.agendaItemId = mapping.agenda_item_id
            folder.agendaConfidence = mapping.confidence
            folder.agendaMethod = mapping.method
            folder.parentFolderId = parent_folder.id if parent_folder else None
            folder.parentPath = parent_path
            folder.depth = node.depth
            folder.folderType = classification.folder_type
            folder.classificationConfidence = classification.confidence
            folder.roundNumber = classification.round_number
            folder.url = node.url

        folder.fileCount = 0
        folder.subtreeFileCount = 0
        folder_by_path[node.normalized_path] = folder
        seen_folder_ids.add(folder_id)
        if mapping.unmapped:
            unmapped.append(folder.normalizedPath)

    root_folder.fileCount = 0
    root_folder.subtreeFileCount = 0

    # --- 8: files, classified and attached to the nearest mapped agenda ------
    def ingest_file(node: TreeNode) -> None:
        parent_path = node.parent_path or ""
        folder = folder_by_path.get(parent_path, root_folder)
        mapping = mapping_by_path.get(parent_path)
        ancestor_names = [n.name for n in node.ancestors() if n.depth > 0]
        classification = classify(node.name, ancestor_names)
        fingerprint = artifact_fingerprint(meeting_id, parent_path, node.name)

        content_hash: str | None = None
        if config.hash_files and (
            not config.hash_only_fl or classification.file_type == "fl_summary"
        ):
            data = source.fetch_bytes(node.url)
            if data:
                content_hash = sha256(data)

        existing = find_existing(
            artifacts, by_hash, fingerprint=fingerprint, content_hash=content_hash
        )
        appearance = DraftArtifactSource(
            sourceType=source_type,
            sourcePath=normalize_path([*node.parts]),
            url=node.url,
            firstSeenAt=detected_at,
            lastSeenAt=detected_at,
            size=node.size,
            modifiedAt=node.modified_at,
        )
        agenda_id = mapping.agenda_item_id if mapping else None

        if existing is None:
            artifact = DraftArtifact(
                id=fingerprint,
                meetingId=meeting_id,
                folderId=folder.id,
                filename=node.name,
                normalizedPath=appearance.sourcePath,
                fileType=classification.file_type,
                classificationConfidence=classification.confidence,
                documentKey=classification.document_key,
                firstSeenAt=detected_at,
                lastSeenAt=detected_at,
                agendaItemId=agenda_id,
                folderPath=parent_path,
                depth=node.depth,
                revision=classification.revision,
                contentHash=content_hash,
                size=node.size,
                modifiedAt=node.modified_at,
                sources=[appearance],
            )
            record_revision(artifact, detected_at)
            artifacts[artifact.id] = artifact
            if content_hash:
                by_hash[content_hash] = artifact.id
            seen_artifact_ids.add(artifact.id)
            if not baseline_scan:
                new_events.append(
                    new_file_event(meeting_id, artifact, detected_at, source_type)
                )
            return

        # Known artifact: a second source appearance is a sync, not an upload.
        existing.lastSeenAt = detected_at
        existing.removedAt = None
        existing.folderId = folder.id
        existing.folderPath = parent_path
        existing.depth = node.depth
        existing.agendaItemId = agenda_id or existing.agendaItemId
        # Re-apply classification so improvements to the rules take effect on
        # already-indexed files instead of only on future uploads.
        existing.fileType = classification.file_type
        existing.classificationConfidence = classification.confidence
        existing.documentKey = classification.document_key
        existing.revision = classification.revision
        merge_source(existing, appearance)
        seen_artifact_ids.add(existing.id)

        if content_changed(
            existing,
            content_hash=content_hash,
            size=node.size,
            modified_at=node.modified_at,
        ):
            existing.contentHash = content_hash or existing.contentHash
            existing.size = node.size
            existing.modifiedAt = node.modified_at
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
            existing.size = existing.size or node.size
            existing.modifiedAt = existing.modifiedAt or node.modified_at

    for node in tree.walk():
        if node.is_dir or node.depth == 0:
            continue
        ingest_file(node)
        parent_path = node.parent_path or ""
        direct = folder_by_path.get(parent_path, root_folder)
        direct.fileCount += 1
        path = parent_path
        while True:
            ancestor = folder_by_path.get(path)
            if ancestor:
                ancestor.subtreeFileCount += 1
            if not path:
                break
            path = path.rsplit("/", 1)[0] if "/" in path else ""

    # --- 9-10: diff against the previous snapshot ----------------------------
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

    for folder in folders.values():
        if (
            folder.id not in seen_folder_ids
            and folder.removedAt is None
            and folder.sourceType == source_type
        ):
            # A disappeared folder is recorded as removed. A rename is never
            # invented from a listing that cannot prove one (§21).
            folder.removedAt = detected_at
            if not baseline_scan:
                new_events.append(
                    removed_folder_event(meeting_id, folder, detected_at, source_type)
                )

    new_events = group_new_folder_events(new_events)
    merged_events = new_events + events
    return DraftIndex(
        meetingId=meeting_id,
        generatedAt=detected_at,
        scanState="baseline" if baseline_scan else "ok",
        lastSuccessfulScanAt=detected_at,
        baselinedAt=baselined_at or detected_at,
        monitoring=monitoring,
        draftsRootUrl=root_url,
        folders=sorted(folders.values(), key=lambda f: f.normalizedPath),
        artifacts=sorted(artifacts.values(), key=lambda a: a.normalizedPath),
        events=merged_events[:MAX_EVENTS],
        newEventIds=[e.id for e in new_events],
        unmappedFolders=sorted(set(unmapped)),
        message=None,
    )
