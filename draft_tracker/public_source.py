"""Public 3GPP draft source.

Locating the drafts tree is discovery, never a hard-coded path: the meeting
folder comes from the 3GPP portal, then candidate sub-folders are probed by
vocabulary ("drafts" inside the meeting inbox). If 3GPP reorganises its
folders, only this module and the directory parser need to change.
"""

from __future__ import annotations

import re

from ingestion.portal import _session as http

from .directory_parser import NormalizedDirectoryEntry, parse_listing

DRAFTS_HINT = re.compile(r"^drafts?$", re.I)
INBOX_HINT = re.compile(r"^in[\s_-]?box$", re.I)


class Public3GPPDraftSource:
    """Reads the public meeting tree over HTTPS directory listings."""

    source_type = "public"

    def __init__(
        self,
        meeting_folder_url: str | None,
        drafts_root_url: str | None = None,
    ):
        self.meeting_folder_url = meeting_folder_url
        self.drafts_root_url = drafts_root_url
        self._cache: dict[str, list[NormalizedDirectoryEntry]] = {}

    # --- discovery ---------------------------------------------------------
    def discover_drafts_root(self) -> str | None:
        if self.drafts_root_url:
            return self.drafts_root_url
        if not self.meeting_folder_url:
            return None
        root = self.meeting_folder_url
        inbox = self._find_child(root, INBOX_HINT)
        for candidate in (inbox, root):
            if not candidate:
                continue
            drafts = self._find_child(candidate, DRAFTS_HINT)
            if drafts:
                return drafts
        return None

    def _find_child(self, url: str, pattern: re.Pattern[str]) -> str | None:
        for entry in self.list_directory(url):
            if entry.is_dir and pattern.match(entry.name.strip()):
                return entry.url
        return None

    # --- listing -----------------------------------------------------------
    def list_directory(self, path: str) -> list[NormalizedDirectoryEntry]:
        if path in self._cache:
            return self._cache[path]
        url = path if path.endswith("/") else path + "/"
        try:
            response = http.get(url, timeout=45)
            response.raise_for_status()
        except Exception:
            return []
        entries = parse_listing(response.text, url)
        self._cache[path] = entries
        return entries

    def fetch_bytes(self, path: str, max_bytes: int = 12 * 1024 * 1024) -> bytes | None:
        try:
            response = http.get(path, timeout=90)
            response.raise_for_status()
        except Exception:
            return None
        content = response.content
        return content if len(content) <= max_bytes else None
