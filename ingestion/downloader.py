"""Discovery and download of 3GPP RAN1 schedule documents.

Architecture follows the public 3GPPSchedule reference project:

  * list the current meeting folder on the 3GPP file server
  * discover the main chair schedule, Chair_notes and sub-chair schedules
    (Hiroki / Sorour / others) by filename pattern, not hard-coded names
  * download only documents whose size/mtime/hash changed since last run

Nothing here is meeting-specific: the meeting is resolved at runtime so
RAN1#127, RAN1#128 and ad-hoc meetings work without code changes.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

BASE_URL = "https://www.3gpp.org/ftp/tsg_ran/WG1_RL1"

MAIN_PATTERNS = [
    re.compile(r"online and offline schedule", re.I),
    re.compile(r"draft.*schedule.*v\d+", re.I),
]
DETAIL_PATTERNS = [
    re.compile(r"schedule for (?P<owner>\w+)", re.I),
    re.compile(r"(?P<owner>hiroki|sorour)[^/]*schedule", re.I),
]
VERSION_RE = re.compile(r"v(\d+(?:[._]\d+)?)", re.I)


@dataclass
class RemoteDocument:
    file_name: str
    url: str
    size: int | None = None
    last_modified: str | None = None

    @property
    def role(self) -> str:
        if any(p.search(self.file_name) for p in DETAIL_PATTERNS):
            return "detail"
        if any(p.search(self.file_name) for p in MAIN_PATTERNS):
            return "main"
        return "detail"

    @property
    def owner(self) -> str | None:
        for pattern in DETAIL_PATTERNS:
            m = pattern.search(self.file_name)
            if m and m.groupdict().get("owner"):
                return m.group("owner").capitalize()
        return "RAN1 Chair" if self.role == "main" else None

    @property
    def version(self) -> str | None:
        m = VERSION_RE.search(self.file_name)
        return "v" + m.group(1).replace("_", ".") if m else None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_state(state_path: Path) -> dict[str, str]:
    if state_path.exists():
        return json.loads(state_path.read_text())
    return {}


def save_state(state_path: Path, state: dict[str, str]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True))


def has_changed(doc_hash: str, file_name: str, state: dict[str, str]) -> bool:
    """Incremental guard: skip re-parsing documents whose bytes are unchanged."""
    return state.get(file_name) != doc_hash


def discover_meeting_folder(listing: list[str]) -> str | None:
    """Pick the newest TSGR1_* folder from a directory listing."""
    folders = [name for name in listing if name.upper().startswith("TSGR1_")]
    if not folders:
        return None

    def sort_key(name: str) -> tuple[int, str]:
        m = re.search(r"TSGR1_(\d+)", name, re.I)
        return (int(m.group(1)) if m else 0, name)

    return sorted(folders, key=sort_key)[-1]
