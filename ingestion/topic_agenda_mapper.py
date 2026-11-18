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
    text = text.lower()
    # "NR-NTN" yields nr, ntn and the joined "nrntn"; "A-IoT" keeps "aiot".
    joined = {w.replace("-", "") for w in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)+", text)}
    text = re.sub(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])", " ", text)
    return {t for t in re.split(r"[^a-z0-9]+", text) if t} | joined


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
        # "R20" is the 5G-Advanced Release 20 work; the 6G study is "6GR".
        return {c for c, t in top_titles.items()
                if re.search(r"rel(?:ease)?[- ]?20", t.lower()) and "6g" not in t.lower()}
    return {c for c, t in top_titles.items() if not re.match(r"\s*(maintenance|pre-)", t.lower())}


def map_topic(
    topic: str, agenda: Iterable[tuple[str, str]], exclude: Iterable[str] = ()
) -> str | None:
    """`exclude`: codes the same block already lists explicitly — the name
    refers to a different item, so they are not candidates."""
    excluded = set(exclude)
    items = [(c, t) for c, t in agenda if c and t and c not in excluded]
    top_titles = {c: t for c, t in items if "." not in c}
    scope = _scope(topic, top_titles)
    wanted = {w for w in _tokens(topic) - IGNORE if "-" not in w}
    # A joined hyphen form ("ntnnr") is only a hint when its parts are not
    # already wanted; matching uses the separate parts.
    parts = set(re.findall(r"[a-z0-9]+", topic.lower()))
    wanted = {w for w in wanted if w in parts or not any(w.startswith(x) for x in parts if len(x) < len(w))}
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
