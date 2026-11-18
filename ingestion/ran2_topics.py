"""RAN2-only: resolve topic names / draft-folder tags to agenda codes.

RAN2 schedules and draft folders name topics ("AIoT offline", "[AI-MOB]",
"RRC modeling") instead of agenda numbers. Each alias points at an agenda
*title* pattern, so the table survives renumbering between meetings. Only a
single unambiguous result is returned; anything else stays unlinked.
RAN1 never calls this module.
"""
from __future__ import annotations

import re

# (topic pattern, agenda-title pattern). Longer/more specific first.
ALIASES: list[tuple[str, str]] = [
    (r"\bntn\s*dlp\b|dl\s*compensation", r"^NR NTN using DL compensation"),
    (r"\bgnss\s*resilient", r"^GNSS resilient"),
    (r"\biot[\s-]*ntn\b", r"^IoT NTN"),
    (r"\bai[\s/-]*(?:ml)?[\s-]*mob", r"^AI/ML for mobility"),
    (r"\bai[\s/-]*(?:ml)?[\s-]*phy\b", r"^AI/ML for PHY"),
    (r"\ba[\s-]?iot\b|ambient\s*iot", r"^Ambient IoT"),
    (r"\blp[\s-]?wus\b", r"LP-WUS"),
    (r"\b6g\s*ntn\b", r"^NTN$"),
    (r"\b6g\s*ai[\s/-]*ml\b", r"^AI/ML$"),
    (r"\b6g\s*mobility\b", r"^Mobility$"),
    (r"\brrc\s*structure", r"^RRC Structure"),
    (r"\bca\b", r"^Spectrum aggregation$"),
    (r"\bnr[\s_-]*others\b", r"^NR Others$"),
    (r"\bisac\b", r"^ISAC$"),
    (r"\brrc\s*model", r"^RRC Modelling"),
    (r"\bsystem\s*information\b", r"^System Information$"),
    (r"\binactive\b", r"^IDLE/INACTIVE$"),
    (r"\bpaging\b", r"^Paging$"),
    (r"\bspectrum\s*aggregation\b", r"^Spectrum aggregation$"),
    (r"\bqos\b", r"^QoS, QoE"),
    (r"\bmeasurements?\b", r"^Measurements$"),
    (r"\b6g\s*up\b|\bup\s+(?:offlines?|upper)|^up\b|user\s*plane", r"^User plane$"),
    (r"\btei\s*20\b", r"^TEI20$"),
    (r"\btei\s*19\b", r"^TEI19$"),
    (r"\bmob\b", r"^Mobility Enh"),
]


def _release_prefix(text: str) -> str | None:
    t = text.lower()
    if re.search(r"\b6g", t):
        return "9"
    if re.search(r"\b(?:nr)?r?20\b|rel-?20", t):
        return "8"
    if re.search(r"\b(?:nr)?r?19\b|rel-?19", t):
        return "7"
    return None


def resolve_topic(text: str, agenda: dict[str, str]) -> str | None:
    """Agenda code for a RAN2 topic name or folder tag, or None if unclear."""
    if not text:
        return None
    low = text.lower()
    for topic_re, title_re in ALIASES:
        if not re.search(topic_re, low):
            continue
        hits = [c for c, t in agenda.items() if re.search(title_re, t or "", re.I)]
        rel = _release_prefix(text)
        if rel:
            narrowed = [c for c in hits if c.split(".")[0] == rel]
            hits = narrowed or hits
        if not hits:
            return None
        if len(hits) == 1:
            return hits[0]
        # Several releases share the title: the latest release is the one a
        # meeting actively works on (older ones are maintenance).
        top = max(int(c.split(".")[0]) for c in hits)
        latest = [c for c in hits if int(c.split(".")[0]) == top]
        return latest[0] if len(latest) == 1 else None
    return None


TAG_RE = re.compile(r"\[(?!AT\d)(?!\d+\])(?!x+\])([^\]]+)\]", re.I)


def folder_topic(name: str) -> str:
    """The topic tag of a RAN2 draft folder: "[AT136][401][AIoT] x" -> "AIoT"."""
    m = TAG_RE.search(name)
    if m:
        return m.group(1)
    # "[AT136][xxx] ISAC pre-meeting offline": no tag, the name is the topic.
    return re.sub(r"\[[^\]]*\]", " ", name).strip() if name.startswith("[") else ""
