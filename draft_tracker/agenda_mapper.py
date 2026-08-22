"""Map draft folder names onto the canonical agenda items of a meeting.

There is exactly one agenda hierarchy in RAN1 Live: the one published with the
schedule (`agenda.json`). Draft folders never create their own hierarchy; they
either resolve to a canonical agenda code or stay `unmapped` for review.

Folder naming is inconsistent between meetings, e.g.

    10.8(ISAC)
    10.8 (ISAC)
    10.8.1 Evaluations
    10.5.4(DL-ctl-ch&sch&HARQ)

so mapping combines: an agenda-number pattern, the mapping inherited from the
nearest mapped ancestor and a normalized-title comparison against the meeting
agenda. Folders that carry no agenda signal at all - "Round 1", "Further
discussion", "ABC discussion", anything a moderator invents mid-week - simply
inherit their ancestor's agenda item. That is the whole rule; no folder name
vocabulary is required for tracking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

CODE_RE = re.compile(r"^\s*(?P<code>\d{1,2}(?:\.\d{1,2}){0,5})\b")


@dataclass(frozen=True)
class AgendaMapping:
    agenda_item_id: str | None
    confidence: float
    method: str

    @property
    def unmapped(self) -> bool:
        return self.agenda_item_id is None


UNMAPPED = AgendaMapping(None, 0.0, "unmapped")


def normalize_name(name: str) -> str:
    text = re.sub(r"[\(\)\[\]_,&/\\-]+", " ", name.lower())
    return re.sub(r"\s+", " ", text).strip()


def extract_code(name: str) -> str | None:
    m = CODE_RE.match(name.replace("\u00a0", " "))
    if not m:
        return None
    code = m.group("code").rstrip(".")
    # A bare year-like or oversized number is not an agenda code.
    return code if len(code.split(".")[0]) <= 2 else None


def _title_of(name: str) -> str:
    code = extract_code(name)
    stripped = name[len(code) :] if code and name.strip().startswith(code) else name
    return normalize_name(stripped)


class AgendaMapper:
    """Resolves folder names against the meeting's canonical agenda items."""

    def __init__(self, agenda_codes: dict[str, str]):
        # code -> title
        self.codes = {c.rstrip("."): t for c, t in agenda_codes.items()}
        self.by_title: dict[str, str] = {}
        for code, title in self.codes.items():
            key = normalize_name(title)
            if key:
                self.by_title.setdefault(key, code)

    def map_folder(self, name: str, parent: AgendaMapping | None) -> AgendaMapping:
        """Map one folder, given the mapping of its nearest mapped ancestor."""
        parent_code = parent.agenda_item_id if parent else None

        code = extract_code(name)
        if code:
            if code in self.codes:
                return AgendaMapping(code, 1.0, "agenda-code")
            # The agenda list may be incomplete (published late): still trust an
            # explicit number when it sits under a known ancestor.
            if parent_code and code.startswith(parent_code + "."):
                return AgendaMapping(code, 0.75, "agenda-code-under-parent")
            if self._nearest_known_ancestor(code):
                return AgendaMapping(code, 0.7, "agenda-code-inferred")
            return AgendaMapping(code, 0.5, "agenda-code-unknown")

        title = _title_of(name)
        if title:
            exact = self.by_title.get(title)
            if exact and (not parent_code or exact.startswith(parent_code)):
                return AgendaMapping(exact, 0.85, "title-exact")
            best, score = self._best_title_match(title, parent_code)
            if best and score >= 0.88:
                return AgendaMapping(best, round(score, 2), "title-similar")

        if parent_code:
            # Any folder with no agenda signal of its own - a round, an FL
            # folder, "Further discussion", "Wednesday" - belongs to the agenda
            # item of its nearest mapped ancestor (§8, §9).
            return AgendaMapping(parent_code, min(parent.confidence if parent else 0.6, 0.6), "inherited-from-ancestor")

        return UNMAPPED

    def _nearest_known_ancestor(self, code: str) -> str | None:
        parts = code.split(".")
        while len(parts) > 1:
            parts.pop()
            candidate = ".".join(parts)
            if candidate in self.codes:
                return candidate
        return None

    def _best_title_match(self, title: str, parent_code: str | None) -> tuple[str | None, float]:
        best: str | None = None
        best_score = 0.0
        for known, code in self.by_title.items():
            if parent_code and not code.startswith(parent_code):
                continue
            score = SequenceMatcher(None, title, known).ratio()
            if score > best_score:
                best, best_score = code, score
        return best, best_score
