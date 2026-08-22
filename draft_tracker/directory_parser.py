"""Adapter that turns a 3GPP FTP directory listing into normalized entries.

Nothing above this module may know what the listing HTML looks like. If 3GPP
changes the layout of its directory pages, only this file changes.

Observed layout (studied against several RAN1 meetings, e.g. TSGR1_125 and
TSGR1_126 `Inbox/drafts/`): a table where each row carries an anchor with the
absolute URL and display name, a "YYYY/MM/DD HH:MM" modification cell and a
size cell that is empty for directories.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import unquote

ROW_RE = re.compile(r"<tr\b.*?</tr>", re.I | re.S)
ANCHOR_RE = re.compile(r'<a\s[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<text>.*?)</a>', re.I | re.S)
CELL_RE = re.compile(r"<td\b[^>]*>(?P<cell>.*?)</td>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
DATE_RE = re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})")
SIZE_RE = re.compile(r"^([\d.,]+)\s*(B|KB|MB|GB)$", re.I)

UNITS = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3}

# Editing side-effects and lock files that must never become draft artifacts.
IGNORED_SUFFIXES = (".checkout", ".checkout.txt", ".tmp", ".lock", ".ds_store")
IGNORED_PREFIXES = ("~$",)


@dataclass(frozen=True)
class NormalizedDirectoryEntry:
    """One folder or file, independent of the listing technology."""

    name: str
    url: str
    is_dir: bool
    modified_at: str | None = None
    size: int | None = None


def _text(html: str) -> str:
    return TAG_RE.sub(" ", html).replace("&nbsp;", " ").strip()


def _parse_date(cell: str) -> str | None:
    m = DATE_RE.search(cell)
    if not m:
        return None
    y, mo, d, h, mi = (int(g) for g in m.groups())
    try:
        return (
            datetime(y, mo, d, h, mi, tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
    except ValueError:
        return None


def _parse_size(cell: str) -> int | None:
    text = _text(cell)
    if not text:
        return None
    m = SIZE_RE.match(text)
    if m:
        value = float(m.group(1).replace(",", ""))
        return int(value * UNITS[m.group(2).lower()])
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def is_ignored(name: str) -> bool:
    lower = name.lower()
    return lower.startswith(IGNORED_PREFIXES) or lower.endswith(IGNORED_SUFFIXES)


def parse_listing(html: str, base_url: str) -> list[NormalizedDirectoryEntry]:
    """Normalized children of `base_url` found in a directory listing page."""
    base = base_url if base_url.endswith("/") else base_url + "/"
    entries: dict[str, NormalizedDirectoryEntry] = {}

    for row in ROW_RE.findall(html):
        cells = CELL_RE.findall(row)
        anchor = None
        for cell in cells:
            match = ANCHOR_RE.search(cell)
            if match and "/ftp/" in match.group("href"):
                anchor = match
                break
        if not anchor:
            continue
        href = anchor.group("href")
        url = href if href.startswith("http") else "https://www.3gpp.org" + href
        if not url.startswith(base) or url.rstrip("/") == base.rstrip("/"):
            continue
        name = _text(anchor.group("text")) or unquote(url.rstrip("/").rsplit("/", 1)[-1])
        if is_ignored(name):
            continue
        modified = next((d for c in cells if (d := _parse_date(c))), None)
        size = None
        for cell in cells[3:]:
            if ANCHOR_RE.search(cell) or _parse_date(cell):
                continue
            size = _parse_size(cell)
            if size:
                break
        has_extension = bool(re.search(r"\.[A-Za-z0-9]{1,6}$", name))
        is_dir = not has_extension and size is None
        entries[url] = NormalizedDirectoryEntry(
            name=name,
            url=url.rstrip("/") + ("/" if is_dir else ""),
            is_dir=is_dir,
            modified_at=modified,
            size=size,
        )

    return sorted(entries.values(), key=lambda e: (not e.is_dir, e.name.lower()))
