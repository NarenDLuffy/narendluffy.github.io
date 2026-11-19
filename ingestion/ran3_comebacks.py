"""RAN3 only: comebacks (CBs) from the chair notes, linked to Drafts folders.

Under each agenda heading the chair writes pink lines "CB: # 2_R19PSCellinfo".
Each has a Drafts folder "CB # 2_R19PSCellinfo". When a comeback is closed the
chair deletes "CB:" and keeps the rest ("# 2_R19PSCellinfo"). Pink marks the
line; the "CB:" text alone decides open/closed. Only active Word text is read
(struck-through/deleted text is ignored). Folders link by name, unique only.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from .docx_active_text import W, active_run_text

PINK = {"FF00FF"}
HEAD_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\.?\s+\S")
LINE_RE = re.compile(r"^\s*(CB\s*:?)?\s*#\s*(?:(\d+)\s*_\s*)?(\S.*?)\s*$", re.I)
FOLDER_RE = re.compile(r"^\s*CB\s*#?\s*(?:(\d+)\s*_\s*)?(\S.*?)\s*$", re.I)


@dataclass
class Comeback:
    name: str
    agendaCode: str
    status: str  # open | closed | removed
    number: str | None = None
    folder: str | None = None

    def to_json(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


def name_key(name: str) -> str:
    k = re.sub(r"[^a-z0-9]", "", name.lower())
    return re.sub(r"rel(?=\d)", "r", k)


def _pink_text(p) -> tuple[str, bool]:
    text, pink = [], False
    for r in p.iter(f"{W}r"):
        t = active_run_text(r)
        if not t:
            continue
        text.append(t)
        c = r.find(f"{W}rPr/{W}color")
        if t.strip() and c is not None and (c.get(f"{W}val") or "").upper() in PINK:
            pink = True
    return "".join(text), pink


def _is_heading(p) -> bool:
    st = p.find(f"{W}pPr/{W}pStyle")
    return st is not None and (st.get(f"{W}val") or "").lower().startswith("heading")


def parse_comebacks(path: str) -> list[Comeback]:
    import docx

    body = docx.Document(path).element.body
    head: str | None = None
    out: dict[str, Comeback] = {}
    for p in body.iter(f"{W}p"):
        text, pink = _pink_text(p)
        if _is_heading(p):
            m = HEAD_RE.match(text)
            head = m.group(1) if m else None  # "10.x.1.2" / "2.5 reminders" handled below
            continue
        if not pink or head is None or "#" not in text:
            continue
        m = LINE_RE.match(text)
        if not m:
            continue
        name = m.group(3)
        # Template/example lines: "# 1_Name", "# n_FolderName" in the reminders section.
        if name.lower() in {"name", "foldername"} or int(head.split(".")[0]) < 3:
            continue
        key = name_key(name)
        if key and key not in out:
            out[key] = Comeback(name=name, agendaCode=head, number=m.group(2),
                                status="open" if m.group(1) else "closed")
    return list(out.values())


def keep_removed(current: list[Comeback], previous: list[dict]) -> list[Comeback]:
    """A comeback missing from the newest notes keeps its last-known agenda item."""
    seen = {name_key(c.name) for c in current}
    for row in previous or []:
        if row.get("name") and name_key(row["name"]) not in seen:
            current.append(Comeback(name=row["name"], agendaCode=row.get("agendaCode", ""),
                                    number=row.get("number"), status="removed", folder=row.get("folder")))
            seen.add(name_key(row["name"]))
    return current


def match_folder(folder_name: str, comebacks: list[Comeback] | list[dict]) -> dict | None:
    """The comeback a "CB # n_Name" folder belongs to: name first, number breaks ties."""
    m = FOLDER_RE.match(folder_name)
    if not m or not re.match(r"^\s*CB\b", folder_name, re.I):
        return None
    rows = [c.to_json() if isinstance(c, Comeback) else c for c in comebacks]
    num, key = m.group(1), name_key(m.group(2))
    hits = [r for r in rows if name_key(r["name"]) == key]
    if not hits and num:  # "CB # 6GAIML1_Usecase" style: the number may be part of the name
        hits = [r for r in rows if name_key(f"{num}{r['name']}") == key or name_key(r["name"]) == name_key(f"{num}_{m.group(2)}")]
    if len(hits) > 1 and num:
        hits = [r for r in hits if r.get("number") == num] or hits
    return hits[0] if len(hits) == 1 else None


def link_folders(comebacks: list[Comeback], folder_names: list[str]) -> tuple[list[str], list[str]]:
    """Fill each comeback's folder; returns (unlinked CB folders, comebacks without folder)."""
    unlinked = []
    for f in folder_names:
        hit = match_folder(f, comebacks)
        if hit is None:
            if re.match(r"^\s*CB\b", f, re.I):
                unlinked.append(f)
            continue
        for c in comebacks:
            if c.name == hit["name"]:
                c.folder = f
    return unlinked, [c.name for c in comebacks if not c.folder and c.status == "open"]
