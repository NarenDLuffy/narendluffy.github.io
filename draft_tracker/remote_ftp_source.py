"""Draft source backed by the remote meeting FTP (see ingestion/remote_ftp.py)."""

from __future__ import annotations

from ingestion import remote_ftp

from .directory_parser import NormalizedDirectoryEntry


class RemoteFtpDraftSource:
    source_type = "public"

    def __init__(self, inbox_url: str):
        self.inbox_url = inbox_url
        self._cache: dict[str, list[NormalizedDirectoryEntry]] = {}

    def discover_drafts_root(self) -> str | None:
        for entry in self.list_directory(self.inbox_url):
            if entry.is_dir and entry.name.strip().lower() in ("drafts", "draft"):
                return entry.url
        return None

    def list_directory(self, path: str) -> list[NormalizedDirectoryEntry]:
        if path not in self._cache:
            self._cache[path] = [
                NormalizedDirectoryEntry(name=n, url=u, is_dir=d, modified_at=m, size=s)
                for n, u, d, m, s in remote_ftp.list_dir(path)
            ]
        return self._cache[path]

    def fetch_bytes(self, path: str, max_bytes: int = 12 * 1024 * 1024) -> bytes | None:
        return remote_ftp.fetch_bytes(path, max_bytes)
