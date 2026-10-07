"""Link schedule blocks that only name a topic ("R20 AI/ML") to an agenda code.

The vocabulary comes entirely from the meeting's agenda titles (chair notes):
words of each title, abbreviations in brackets ("(AI)", "(ML)") and joined
initial forms ("Ambient IoT" -> "aiot"). Nothing is hard-coded per meeting.
A block is linked only when exactly one agenda item matches best.
"""

from __future__ import annotations

import re
from typing import Iterable

IGNORE = {"nr", "for", "and", "the", "of", "in", "on", "phase", "r20", "6gr", "rel", "release",
          "session", "discussion", "e", "utra", "with", "to", "a", "r", "gr", "g"}


def _tokens(text: str) -> set[str]:
    text = text.lower().replace("-", "")
    text = re.sub(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])", " ", text)
    return {t for t in re.split(r"[^a-z0-9]+", text) if t}


def _title_vocab(title: str) -> set[str]:
    vocab = _tokens(title)
    words = re.findall(r"[A-Za-z0-9]+", title)
    for a, b in zip(words, words[1:]):
        vocab.add((a[0] + b).lower())  # "Ambient IoT" -> "aiot"
    return vocab


def _scope(topic: str, top_titles: dict[str, str]) -> set[str]:
    low = topic.lower()
    if re.search(r"\b6gr?\b", low):
        return {c for c, t in top_titles.items() if "6g" in t.lower()}
    if re.search(r"\br(?:el)?-?20\b", low):
        return {c for c, t in top_titles.items() if re.search(r"rel(?:ease)?[- ]?20", t.lower())}
    return {c for c, t in top_titles.items() if not re.match(r"\s*(maintenance|pre-)", t.lower())}


def map_topic(topic: str, agenda: Iterable[tuple[str, str]]) -> str | None:
    items = [(c, t) for c, t in agenda if c and t]
    top_titles = {c: t for c, t in items if "." not in c}
    scope = _scope(topic, top_titles)
    wanted = _tokens(topic) - IGNORE
    wanted = {w for w in wanted if not w.isdigit()}
    if not wanted or not scope:
        return None
    best: list[str] = []
    for code, title in items:
        if code.count(".") != 1 or code.split(".")[0] not in scope:
            continue
        if wanted <= _title_vocab(title):
            best.append(code)
    return best[0] if len(best) == 1 else None
