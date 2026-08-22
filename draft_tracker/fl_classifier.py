"""Classify a draft file by its role in the discussion.

Conventions vary between moderators, so classification is deliberately fuzzy
and never invents a result: anything that is not clearly recognised stays
`generic_draft`, or `unknown` for files that are not discussion documents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

FL_PATTERNS = (
    r"\bfl[\s_-]*summary\b",
    r"\bfls\b",
    r"\bfls[_\s-]",
    r"\bfeature\s*lead\b",
    r"\bsummary\s+(?:on|of|for)\b",
    r"\bmoderator[\s_-]*summary\b",
    r"^summary\b",
    r"\bfl[\s_-]*(?:draft|report)\b",
)
CHAIR_PATTERNS = (r"\bchair\b", r"\bchairman\b", r"\bsession\s*notes\b", r"\bagenda\b")
DRAFT_EXTENSIONS = (".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".pdf", ".zip", ".txt")

REVISION_RE = re.compile(r"[_\s-]v(?P<num>\d{1,3})(?P<tail>[_\s-].*)?$", re.I)
TDOC_RE = re.compile(r"\bR1-\d{2}[0-9x]{4,5}\b", re.I)

FileType = str  # "fl_summary" | "chair_draft" | "generic_draft" | "unknown"


@dataclass(frozen=True)
class Classification:
    file_type: FileType
    confidence: float
    """Filename with revision/authors stripped: groups revisions of one document."""
    document_key: str
    revision: int | None


def _stem(filename: str) -> str:
    return filename.rsplit(".", 1)[0] if "." in filename else filename


def document_key(filename: str) -> tuple[str, int | None]:
    """Stable key for "the same document across revisions", plus its revision."""
    stem = _stem(filename)
    revision: int | None = None
    m = REVISION_RE.search(stem)
    if m:
        revision = int(m.group("num"))
        stem = stem[: m.start()]
    stem = TDOC_RE.sub("", stem)
    stem = re.sub(r"[^a-z0-9]+", " ", stem.lower()).strip()
    return stem or _stem(filename).lower(), revision


def classify(filename: str, folder_names: list[str]) -> Classification:
    # Separators are inconsistent (FL_Summary, FLS-v01, fl summary), so match
    # against a space-normalised form where word boundaries actually hold.
    lower = re.sub(r"[^a-z0-9]+", " ", filename.lower()).strip()
    key, revision = document_key(filename)
    context = " ".join(
        [lower, *[re.sub(r"[^a-z0-9]+", " ", f.lower()) for f in folder_names]]
    )

    if not filename.lower().endswith(DRAFT_EXTENSIONS):
        return Classification("unknown", 0.3, key, revision)


    if not lower.endswith(DRAFT_EXTENSIONS):
        return Classification("unknown", 0.3, key, revision)

    if any(re.search(p, lower) for p in FL_PATTERNS):
        return Classification("fl_summary", 0.9, key, revision)
    if any(re.search(p, context) for p in FL_PATTERNS):
        return Classification("fl_summary", 0.6, key, revision)
    if any(re.search(p, lower) for p in CHAIR_PATTERNS):
        return Classification("chair_draft", 0.7, key, revision)
    return Classification("generic_draft", 0.5, key, revision)
