"""SA1/SA2 Drafts: link files by tdoc number and folders by work-item acronym.

* Files: a draft name carries tdoc numbers ("draft S1-264378 was 4113 AI Training",
  "S2-2612574_was_S2-2612106 …"). The meeting's TDoc_List_Meeting_<G>#<n>.xlsx
  (Docs/) gives each tdoc's agenda item. The file's own number is tried first,
  then the ones it was revised from; short "was 4113" numbers take the prefix of
  the file's full number. No listed tdoc -> no link.
* Folders (SA2 "R20 Sensing-ARC", "FS_enIMS_ARC"): the name, minus "R<rel>" and
  "(SID)", must equal (or uniquely prefix) the acronym in an agenda title's last
  brackets, inside that release's section when one is given. Several hits that
  share a parent ("FS_6G_ARC" -> 20.6.x) link the parent; otherwise nothing.
"""

from __future__ import annotations

import io
import re

TDOC_RE = re.compile(r"(?<![0-9])(S[1-6])-(\d{6,7})", re.I)
SHORT_RE = re.compile(r"(?:was|rev(?:ision)?(?:\s*of)?|-)[\s_-]*(?:S[1-6]-)?((?:\d{4,5})(?:[_\s]\d{4,5})*)(?!\d)", re.I)


def tdocs_in(name: str) -> list[str]:
    full = [(m.group(1).upper(), m.group(2)) for m in TDOC_RE.finditer(name)]
    out = [f"{g}-{n}" for g, n in full]
    if full:
        g, n = full[0]
        for m in SHORT_RE.finditer(TDOC_RE.sub(" ", name)):
            for short in re.split(r"[_\s]", m.group(1)):
                if len(short) < len(n):
                    out.append(f"{g}-{n[: len(n) - len(short)]}{short}")
    return list(dict.fromkeys(out))


def parse_tdoc_list(data: bytes) -> dict[str, str]:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    head = [str(h or "").strip().lower() for h in next(rows, [])]
    try:
        ti, ai = head.index("tdoc"), head.index("agenda item")
    except ValueError:
        return {}
    out = {}
    for r in rows:
        t, a = (r[ti] if ti < len(r) else None), (r[ai] if ai < len(r) else None)
        if t and a and re.fullmatch(r"\d+(?:\.\d+)*", str(a).strip()):
            out[str(t).strip().upper()] = str(a).strip()
    return out


def file_code(name: str, tdoc_agenda: dict[str, str]) -> str | None:
    for t in tdocs_in(name):
        if t in tdoc_agenda:
            return tdoc_agenda[t]
    return None


def _key(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def folder_code(name: str, codes: dict[str, str]) -> str | None:
    rel = re.match(r"^\s*R(\d{2})\s+", name, re.I)
    rest = name[rel.end():] if rel else name
    rest = re.sub(r"\(?\b(SID|WID)\b\)?", " ", rest, flags=re.I)
    fk = _key(rest)
    if len(fk) < 4:
        return None
    acr = {}
    for code, title in codes.items():
        m = re.findall(r"\(([^()]+)\)", title or "")
        if m and (not rel or code.startswith(rel.group(1) + ".")):
            acr[code] = _key(m[-1])
    hits = [c for c, k in acr.items() if k == fk] or [c for c, k in acr.items() if k == "fs" + fk]
    if not hits:
        hits = [c for c, k in acr.items() if k.startswith(fk)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        parts = [h.split(".") for h in hits]
        common = []
        for xs in zip(*parts):
            if len(set(xs)) != 1:
                break
            common.append(xs[0])
        if len(common) >= 2:
            return ".".join(common)
    return None


def make_resolver(codes: dict[str, str], tdoc_agenda: dict[str, str]):
    def resolve(name: str):
        return folder_code(name, codes)

    resolve.file_code = lambda name: file_code(name, tdoc_agenda)  # type: ignore[attr-defined]
    return resolve
