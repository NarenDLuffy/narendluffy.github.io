"""Source abstraction shared by the public 3GPP tree and the meeting-local one.

The tracker only ever talks to a `DraftSource`. The meeting-local server
(typically http://10.10.10.10) is *not* reachable from GitHub Actions and may
not be reachable from a browser either, so it is modelled as an optional
implementation that can later be provided by a helper app, companion service,
bridge or manual upload without touching the tracker, the model or the UI.

Failing to reach a meeting-local source is a normal condition: it yields an
empty scan, never an application error.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .directory_parser import NormalizedDirectoryEntry


@runtime_checkable
class DraftSource(Protocol):
    source_type: str  # "public" | "meeting-local"

    def discover_drafts_root(self) -> str | None:
        """URL/path of this meeting's drafts tree, or None when unavailable."""

    def list_directory(self, path: str) -> list[NormalizedDirectoryEntry]:
        """Direct children of a directory; empty when unreachable."""

    def fetch_bytes(self, path: str) -> bytes | None:
        """File content when the source allows it, else None (metadata only)."""


class MeetingLocalDraftSource:
    """Placeholder implementation for the venue server.

    It deliberately reports "unavailable" until a transport (helper app, local
    companion, bridge) is configured. Artifacts submitted by such a transport
    are merged through the same artifact matcher as the public source, so a
    document seen locally first and publicly later stays one artifact.
    """

    source_type = "meeting-local"

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url

    def discover_drafts_root(self) -> str | None:
        return None

    def list_directory(self, path: str) -> list[NormalizedDirectoryEntry]:  # noqa: ARG002
        return []

    def fetch_bytes(self, path: str) -> bytes | None:  # noqa: ARG002
        return None
