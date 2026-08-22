"""Persistence of draft-tracking state.

State lives in the published index itself (`public/data/meetings/<slug>/
drafts.json`), which is committed by the refresh workflow. That makes every
scan stateful without a separate database: the previous published index is the
previous snapshot. A failed scan never erases it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MEETINGS_DIR = Path("public/data/meetings")


def index_path(slug: str) -> Path:
    return MEETINGS_DIR / slug / "drafts.json"


def load_previous(slug: str) -> dict[str, Any] | None:
    path = index_path(slug)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def save_index(slug: str, payload: dict[str, Any]) -> Path:
    path = index_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    return path
