"""Which schedule cells a chair actually edited ("latest change" rule).

Secondary chairs copy the shared grid into their own notes and rarely touch it
again, so counting files lets stale copies out-vote a fresh edit. Every block
gets introducedAt: when its content first appeared in its own document family,
found by walking back through the family's revisions while the block is still
there. Revision time is the document's own saved time (docProps/core.xml).

Each revision's block signatures are kept in edit-history.json, so an older
revision is downloaded and parsed once per meeting, never on every run.

introducedAt is "" when unknown (first release, no older revision): ranking
then falls back to the older rules, and unknown never beats a known edit.
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from .models import Session

HISTORY_NAME = "edit-history.json"
ROOT = Path("public/data/meetings")


def _codes(items: list[str]) -> tuple[str, ...]:
    return tuple(sorted(re.sub(r"\.x$", "", c.strip().lower()) for c in items if c.strip()))


def signature(session: Session) -> str:
    """Normalised meaning of one block: day, room lane, time, items, splits.

    Row position, spacing, dash type and x/X case never count as an edit.
    """
    slots = [
        [re.sub(r"\.x$", "", (s.code or "").lower()), s.minutes, s.startTime, s.endTime]
        for s in (session.agendaBreakdown or [])
    ]
    key = [session.date, session.roomId, session.startTime, session.endTime, list(_codes(session.agendaItems)), slots]
    return json.dumps(key, separators=(",", ":"))


def revision_time(path: str, fallback: str) -> str:
    """The document's own last-saved time, ISO; fallback when absent."""
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("docProps/core.xml").decode("utf-8", "ignore")
        m = re.search(r"<dcterms:modified[^>]*>([^<]+)<", xml)
        if m:
            return m.group(1).strip()
    except (OSError, KeyError, zipfile.BadZipFile):
        pass
    return fallback


def load_history(slug: str, root: Path = ROOT) -> dict:
    try:
        data = json.loads((root / slug / HISTORY_NAME).read_text())
        return data if isinstance(data, dict) and data.get("version") == 2 else {"version": 2}
    except (OSError, json.JSONDecodeError):
        return {"version": 2}


def save_history(slug: str, history: dict, root: Path = ROOT) -> None:
    path = root / slug / HISTORY_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=1, sort_keys=True))


def record_revision(history: dict, family: str, file_name: str, at: str, sessions: list[Session]) -> None:
    history.setdefault("families", {}).setdefault(family, {})[file_name] = {
        "at": at,
        "sigs": sorted({signature(s) for s in sessions}),
    }


def known(history: dict, family: str, file_name: str) -> bool:
    return file_name in history.get("families", {}).get(family, {})


def mark_edits(history: dict, family: str, latest_name: str, older_names: list[str], sessions: list[Session]) -> int:
    """Stamp introducedAt on every ref of `sessions` (the latest revision).

    older_names is newest first. Returns how many blocks differ from the
    previous revision (0 when there is none).
    """
    revs = history.get("families", {}).get(family, {})
    latest_at = revs.get(latest_name, {}).get("at", "")
    chain = [(revs[n]["at"], set(revs[n]["sigs"])) for n in older_names if n in revs]
    edits = 0
    for session in sessions:
        sig = signature(session)
        stamp = ""
        if chain:
            stamp = latest_at
            for at, sigs in chain:
                if sig not in sigs:
                    break
                stamp = at
            if sig not in chain[0][1]:
                edits += 1
        for ref in session.sources:
            ref.introducedAt = stamp or None
    return edits
