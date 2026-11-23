"""Conditional ("only if changed") downloads for 3GPP documents.

Every fetched body is kept under .ingestion-state/http-cache (restored between
workflow runs by actions/cache) with its ETag/Last-Modified. The next run sends
If-None-Match / If-Modified-Since, so an unchanged file costs the 3GPP server a
304 instead of the full document.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import requests

CACHE_DIR = Path(os.environ.get("HTTP_CACHE_DIR", ".ingestion-state/http-cache"))
_session = requests.Session()


def _paths(url: str) -> tuple[Path, Path]:
    h = hashlib.sha256(url.encode()).hexdigest()[:32]
    return CACHE_DIR / f"{h}.body", CACHE_DIR / f"{h}.json"


def cached_get(url: str, timeout: float = 60, session: requests.Session | None = None) -> bytes | None:
    """Body of url, reusing the cached copy when the server answers 304."""
    s = session or _session
    body_p, meta_p = _paths(url)
    headers: dict[str, str] = {}
    meta: dict[str, str] = {}
    if body_p.exists() and meta_p.exists():
        try:
            meta = json.loads(meta_p.read_text())
        except ValueError:
            meta = {}
        if meta.get("etag"):
            headers["If-None-Match"] = meta["etag"]
        if meta.get("last_modified"):
            headers["If-Modified-Since"] = meta["last_modified"]
    try:
        r = s.get(url, timeout=timeout, headers=headers)
    except Exception:  # noqa: BLE001
        return body_p.read_bytes() if body_p.exists() else None
    if r.status_code == 304 and body_p.exists():
        return body_p.read_bytes()
    if not r.ok:
        return None
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        body_p.write_bytes(r.content)
        meta_p.write_text(json.dumps({
            "url": url,
            "etag": r.headers.get("ETag", ""),
            "last_modified": r.headers.get("Last-Modified", ""),
        }))
    except OSError:
        pass
    return r.content
