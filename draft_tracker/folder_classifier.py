"""Optional semantic labels for a discovered folder.

Classification is a *hint on top of* the discovered tree, never a requirement
for tracking. Anything unrecognised stays "generic": the tracker still lists
it, diffs it, and notifies about files inside it.

Never force a folder into a round model. "Further discussion", "Wednesday",
"Agreement discussion" are simply generic folders.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

FolderType = str  # agenda | round | fl | topic | generic | unknown

# Only shapes that unambiguously mean "discussion round".
ROUND_RES = (
    re.compile(r"^\s*round\s*[#-]?\s*(?P<n>\d{1,2})\b", re.I),
    re.compile(r"^\s*round(?P<n>\d{1,2})\b", re.I),
    re.compile(r"^\s*r(?P<n>\d{1,2})\s*$", re.I),
    re.compile(r"^\s*rd\.?\s*(?P<n>\d{1,2})\b", re.I),
)
FL_RE = re.compile(r"^\s*(fl|fls|feature\s*lead|moderator)(\s|[_\-]|$)", re.I)
AGENDA_CODE_RE = re.compile(r"^\s*\d{1,2}(\.\d{1,2}){0,5}\b")


@dataclass(frozen=True)
class FolderClassification:
    folder_type: FolderType
    confidence: float
    round_number: int | None = None


def round_number(name: str) -> int | None:
    """Round number when the folder name unambiguously denotes a round."""
    for pattern in ROUND_RES:
        m = pattern.match(name.strip())
        if m:
            return int(m.group("n"))
    return None


def classify_folder(name: str, *, has_agenda_code: bool, is_agenda_root: bool) -> FolderClassification:
    stripped = name.strip()
    n = round_number(stripped)
    if n is not None:
        return FolderClassification("round", 0.9, n)
    if FL_RE.match(stripped):
        return FolderClassification("fl", 0.8)
    if is_agenda_root and has_agenda_code:
        return FolderClassification("agenda", 0.95)
    if has_agenda_code:
        return FolderClassification("agenda", 0.8)
    if AGENDA_CODE_RE.match(stripped):
        return FolderClassification("topic", 0.4)
    if not stripped:
        return FolderClassification("unknown", 0.0)
    return FolderClassification("generic", 0.0)
