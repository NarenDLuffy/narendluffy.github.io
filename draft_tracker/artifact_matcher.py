"""Identity and de-duplication for draft artifacts.

The same upload can appear twice: first on the meeting-local server, later on
the public 3GPP site. It must stay ONE artifact with two source appearances,
so the user gets one notification.

Identity, strongest first:
  1. meeting + content hash (SHA-256), when bytes were fetched
  2. meeting + normalized agenda path + normalized filename
Modification timestamps are never used alone.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from .models import DraftArtifact, DraftArtifactSource


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_path(parts: list[str]) -> str:
    cleaned = [re.sub(r"\s+", " ", p).strip().lower() for p in parts if p]
    return "/".join(cleaned)


def normalize_filename(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().lower()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]
    return f"{prefix}_{digest}"


def artifact_fingerprint(meeting_id: str, folder_path: str, filename: str) -> str:
    return stable_id("art", meeting_id, folder_path, normalize_filename(filename))


def find_existing(
    artifacts: dict[str, DraftArtifact],
    by_hash: dict[str, str],
    *,
    fingerprint: str,
    content_hash: str | None,
) -> DraftArtifact | None:
    if content_hash and content_hash in by_hash:
        return artifacts.get(by_hash[content_hash])
    return artifacts.get(fingerprint)


def merge_source(artifact: DraftArtifact, appearance: DraftArtifactSource) -> bool:
    """Attach a source appearance. Returns True when the source is new.

    A new *source* for a known artifact is a synchronization event, not a new
    upload, and never produces a user notification.
    """
    for existing in artifact.sources:
        if existing.sourceType == appearance.sourceType and existing.sourcePath == appearance.sourcePath:
            existing.lastSeenAt = appearance.lastSeenAt
            existing.size = appearance.size or existing.size
            existing.modifiedAt = appearance.modifiedAt or existing.modifiedAt
            return False
    artifact.sources.append(appearance)
    return True


def content_changed(
    artifact: DraftArtifact,
    *,
    content_hash: str | None,
    size: int | None,
    modified_at: str | None,
) -> bool:
    """True only for a real content change, not a re-synchronization."""
    if content_hash and artifact.contentHash:
        return content_hash != artifact.contentHash
    if content_hash and not artifact.contentHash:
        return False  # first time we hashed a known file: not a change
    if size is not None and artifact.size is not None and size != artifact.size:
        return True
    if (
        size is not None
        and artifact.size is not None
        and size == artifact.size
        and modified_at
        and artifact.modifiedAt
        and modified_at != artifact.modifiedAt
    ):
        # Same bytes count with a new timestamp is usually a re-sync: ignore.
        return False
    return False


def record_revision(artifact: DraftArtifact, seen_at: str) -> None:
    artifact.revisions.append(
        {
            "revision": len(artifact.revisions) + 1,
            "contentHash": artifact.contentHash,
            "size": artifact.size,
            "modifiedAt": artifact.modifiedAt,
            "firstSeenAt": seen_at,
        }
    )
