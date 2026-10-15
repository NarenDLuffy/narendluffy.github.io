"""Which schedule cells a chair actually edited ("latest change" rule).

Secondary chairs copy the shared grid into their own notes and rarely touch it
again, so counting files lets stale copies out-vote a fresh edit. Each parsed
block is compared with the previous revision of its own document family; a
block that differs (or is new) was introduced by this revision. The time a
block was first seen is kept in edit-history.json, so an edit made in v05
still beats untouched copies when v06 leaves it alone.

introducedAt is "" when unknown (first release, no history): ranking then
falls back to the older rules, and unknown never beats a known edit.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .models import Session

HISTORY_NAME = "edit-history.json"


def _codes(items: list[str]) -> tuple[str, ...]:
    return tuple(sorted(re.sub(r"\.x$", "", c.strip().lower()) for c in items if c.strip()))


def signature(session: Session) -> str:
    """Normalised meaning of one block: day, room lane, time, items, splits.

    Row position, spacing, dash type and x/X case never count as an edit.
    """
    slots = tuple(
        (
            re.sub(r"\.x$", "", (s.code or "").lower()),
            s.minutes,
            s.startTime,
            s.endTime,
        )
        for s in (session.agendaBreakdown or [])
    )
    key = (session.date, session.roomId, session.startTime, session.endTime, _codes(session.agendaItems), slots)
    return json.dumps(key, separators=(",", ":"))


def load_history(slug: str, root: Path = Path("public/data/meetings")) -> dict[str, dict[str, str]]:
    path = root / slug / HISTORY_NAME
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_history(slug: str, history: dict[str, dict[str, str]], root: Path = Path("public/data/meetings")) -> None:
    path = root / slug / HISTORY_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=1, sort_keys=True))


def mark_edits(
    family: str,
    latest: list[Session],
    previous: list[Session] | None,
    history: dict[str, dict[str, str]],
    seen_at: str,
) -> int:
    """Stamp introducedAt on every source ref of `latest`; returns edits found.

    * previous is None (first release) -> history value, else unknown.
    * signature absent from previous   -> edited now (history keeps an older stamp
      when the same content returns after a revert).
    * signature present in previous    -> history value, else unknown.
    """
    fam = history.setdefault(family, {})
    before = {signature(s) for s in previous} if previous is not None else None
    edits = 0
    for session in latest:
        sig = signature(session)
        stamp = fam.get(sig, "")
        if before is not None and sig not in before:
            if not stamp:
                stamp = seen_at
                fam[sig] = stamp
            edits += 1
        for ref in session.sources:
            ref.introducedAt = stamp or None
    return edits
