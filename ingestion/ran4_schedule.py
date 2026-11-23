"""RAN4 schedule: the chair's "RAN4_<n>_meeting_schedule_vNN[_after_DAY].pptx".

* Source: Meetings_3GPP_SYNC/RAN4/Inbox/Meeting_Arrangements (+ History), and
  the meeting's own Inbox/Meeting_Arrangements outside meeting days. Every name
  carries the meeting number, so Sync is always safe to read. Highest vNN wins.
* One slide per weekday (title "Monday"…; an untitled slide follows the
  previous day). Its table: rooms across ("RAN4 Main (Yang Session)", the two
  breakouts, "Ad hoc room"), "9:30-10:30" rows down. A row holding only
  "Coffee break"/"Lunch break" is a break (shown in Main).
* Inside a cell the chair writes the times: "—12:00—" / "17:30" lines split the
  cell, "(14:30 – 15:30)" or "8:00-9:00" opens a timed part, "Start at 8:30" /
  "(Start from 9:00)" moves the start. "Coffee break AH: …" / "Lunch break AH
  (13.30-14.30): …" is an ad-hoc held during the neighbouring break.
* Agenda codes come from the topic numbers ("[201]", "[101-A]") through the
  chair's "List_Topics_moderators" workbook (column "AI covered…"); a bare
  "[105]" covers 105-A and 105-B. No topic list -> no codes, never guessed.
Shared rules (ingestion/AGENTS.md): struck-through text is dropped, times are
never invented, overlaps refuse the publish.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

import ingestion.remote_ftp as remote_ftp

from .meeting_discovery import compute_status
from .models import (
    AgendaItem,
    AgendaSlot,
    IngestStatus,
    Meeting,
    MeetingSourceFolders,
    Room,
    ScheduleBundle,
    ScheduleSource,
    Session,
    SessionSourceRef,
)
from .portal import PortalMeeting, list_folder
from .ran2_schedule import PROBLEMS, WEEKDAYS, _day_date, _iso
from .ran3_schedule import _fmt, _room, _session, _source, overlap_problems
import copy

from .ranp_schedule import parse_agenda_csv

SYNC_ARR = "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN4/Inbox/Meeting_Arrangements/"
D = r"[-–—~]"
RANGE_RE = re.compile(rf"(\d{{1,2}})[:.](\d{{2}})\s*{D}\s*(\d{{1,2}})[:.](\d{{2}})")
MARK_RE = re.compile(r"^[\s~–—-]*(\d{1,2})[:.](\d{2})[\s~–—-]*$")
START_RE = re.compile(r"start\s*(?:at|from)\s*(\d{1,2})[:.](\d{2})", re.I)
BREAK_ROW_RE = re.compile(r"^\s*(?:(coffee|lunch)\s*break|(茶歇)|(午餐|午饭))\s*$", re.I)
BREAK_AH_RE = re.compile(r"^\s*\[?\s*(coff?r?e+|lu?n?ch)\s*-?\s*break\b(.*)$", re.I)
BREAK_HEAD_RE = re.compile(r"^\s*\[?\s*[A-Za-z]+\s*-?\s*break\s*(?:ad[\s-]*hoc|AH|offline)?\s*\]?[\s():]*", re.I)
TOPIC_RE = re.compile(r"\[?(\d{3})(?:-([A-Z](?:/[A-Z])*))?\]|(?<![\d\[])(\d{3})-\[?([A-Z](?:/[A-Z])*)\]?")
EOM_SHOWN = 18 * 60  # display end for "EOM" rows, labelled "(until end of meeting)"
ADHOC_RE = re.compile(r"ad[\s-]*hoc|\bAH\b", re.I)


def schedule_re(number: int, bis: bool) -> re.Pattern[str]:
    b = r"[_\s-]*bis" if bis else r"(?![_\s-]*bis)"
    return re.compile(rf"^RAN4[_\s#-]*{number}{b}[_\s-]*meeting[_\s-]*schedule[_\s-]*v(\d+)[^/]*\.pptx$", re.I)


def topics_re(number: int, bis: bool) -> re.Pattern[str]:
    b = r"[_\s-]*bis" if bis else r"(?![_\s-]*bis)"
    return re.compile(rf"^List[_\s-]*Topics.*?RAN4[_\s#-]*{number}{b}[^/]*?v(\d+)\.xlsx$", re.I)


def _version(pat: re.Pattern[str], name: str) -> int:
    m = pat.search(name)
    return int(m.group(1)) if m else -1


def _m(h: str, mi: str) -> int:
    return int(h) * 60 + int(mi)


# ---------- topic list ----------

def parse_topics(path: str) -> dict[str, list[str]]:
    """{"201": ["7.4.2", …], "101-A": [...]} from every sheet of the topic workbook."""
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out: dict[str, list[str]] = {}
    for ws in wb:
        ai_col = None
        for row in ws.iter_rows(values_only=True):
            cells = ["" if v is None else str(v).strip() for v in row]
            if ai_col is None:
                for i, c in enumerate(cells):
                    lc = c.lower()
                    if lc == "ai" or lc.startswith("ai covered"):
                        ai_col = i
                        break
                continue
            tid = cells[0] if cells else ""
            if re.fullmatch(r"\d{3}(?:\.0)?", tid):
                tid = tid[:3]
            if not re.fullmatch(r"\d{3}(?:-[A-Z])?", tid) or ai_col >= len(cells):
                continue
            codes = re.findall(r"(?<![\d.])\d{1,2}(?:\.\d{1,2})*(?![\d.])", cells[ai_col])
            if codes:
                out[tid] = list(dict.fromkeys(codes))
    return out


def topic_ids(text: str) -> list[str]:
    ids: list[str] = []
    for m in TOPIC_RE.finditer(text):
        if m.group(1):
            ids += [m.group(1) + f"-{x}" for x in m.group(2).split("/")] if m.group(2) else [m.group(1)]
        else:
            ids += [f"{m.group(3)}-{s}" for s in m.group(4).split("/")]
    return list(dict.fromkeys(ids))


def codes_for(text: str, topics: dict[str, list[str]]) -> list[str]:
    codes: list[str] = []
    for tid in topic_ids(text):
        hits = [tid] if tid in topics else [k for k in topics if k.startswith(tid + "-")]
        for h in hits:
            codes += topics[h]
    return list(dict.fromkeys(codes))


# ---------- slides ----------

def _cell_lines(cell) -> list[str]:
    """Paragraph texts of a table cell without struck-through runs."""
    lines = []
    for p in cell.text_frame.paragraphs:
        parts = []
        for r in p.runs:
            rpr = r._r.find("{http://schemas.openxmlformats.org/drawingml/2006/main}rPr")
            if rpr is not None and rpr.get("strike") not in (None, "noStrike"):
                continue
            parts.append(r.text)
        lines.append("".join(parts).replace("\x0b", " ").strip())
    return lines


@dataclass
class _Seg:
    start: int | None
    end: int | None = None
    lines: list[str] = field(default_factory=list)
    kind: str = ""  # "", "coffee", "lunch"
    gap: bool = False  # blank line seen after text


def split_cell(lines: list[str]) -> list[_Seg]:
    """Cut a cell into parts at the times the chair wrote; untimed parts keep None."""
    segs: list[_Seg] = [_Seg(None)]

    def open_(seg: _Seg):
        if not segs[-1].lines and not segs[-1].kind and segs[-1].start is None and segs[-1].end is None:
            segs[-1] = seg
        else:
            segs.append(seg)

    container: _Seg | None = None
    for line in lines:
        cur = segs[-1]
        if not line:
            cur.gap = bool(cur.lines)
            continue
        if (mk := MARK_RE.match(line)):
            t = _m(*mk.groups())
            if cur.end is None:
                cur.end = t
            segs.append(_Seg(t))
            continue
        b = BREAK_AH_RE.match(line)
        if b and not BREAK_ROW_RE.match(line) and (ADHOC_RE.search(line) or ":" in line or b.group(2).strip()):
            rng = RANGE_RE.search(line)
            seg = _Seg(None, kind="lunch" if b.group(1).lower().startswith("l") else "coffee")
            rest = line
            if rng:
                seg.start, seg.end = _m(*rng.groups()[:2]), _m(*rng.groups()[2:])
                rest = RANGE_RE.sub("", rest)
            rest = BREAK_HEAD_RE.sub("", re.sub(r"\(\s*\)", "", rest)).strip()
            if rest:
                seg.lines.append(rest)
            segs.append(seg)
            container = None
            continue
        rng = RANGE_RE.search(line)
        st = START_RE.search(line)
        if rng:
            text = re.sub(r"\(\s*\)|start\s*at", "", RANGE_RE.sub("", line), flags=re.I).strip(" :()")
            a, b2 = _m(*rng.groups()[:2]), _m(*rng.groups()[2:])
            if container and container.start <= a < b2 <= container.end and (a, b2) != (container.start, container.end):
                # A timed line inside a timed heading splits that heading's time.
                if segs[-1] is container and len(container.lines) <= 1:
                    segs.pop()
                head = container.lines[:1]
                segs.append(_Seg(a, b2, head + ([text] if text else [])))
                continue
            seg = _Seg(a, b2, [text] if text else [])
            open_(seg)
            container = seg
            continue
        if st:
            text = re.sub(r"\(?\s*start\s*(?:at|from)\s*\d{1,2}[:.]\d{2}\s*\)?", "", line, flags=re.I).strip(" :")
            open_(_Seg(_m(*st.groups()), None, [text] if text else []))
            continue
        if cur.gap and (cur.kind or cur.end is not None):
            # A timed or break part ends at its first blank line; the cell resumes.
            segs.append(_Seg(cur.end if not cur.kind else None))
            cur = segs[-1]
        cur.gap = False
        cur.lines.append(line)
    segs = [s for s in segs if s.lines]
    timed = [s for s in segs if not s.kind]
    for prev, nxt in zip(timed, timed[1:]):
        if nxt.start is None and prev.end is not None:
            nxt.start = prev.end
        if prev.end is None and nxt.start is not None:
            prev.end = nxt.start
    return segs


@dataclass
class _Row:
    s: int
    e: int | None
    cells: dict[int, list[str]]
    brk: str | None  # "coffee" / "lunch" for a break row


def parse_schedule(path: str, meeting: Meeting, source: ScheduleSource, topics: dict[str, list[str]]):
    from pptx import Presentation

    prs = Presentation(path)
    sessions: list[Session] = []
    problems: list[str] = []
    rooms: dict[int, Room] = {}
    day_idx = -1
    by_day: dict[int, object] = {}
    for slide in prs.slides:
        if slide._element.get("show") == "0":
            continue  # hidden slide
        title = (slide.shapes.title.text if slide.shapes.title is not None else "").strip().lower()
        tables = [sh.table for sh in slide.shapes if getattr(sh, "has_table", False)]
        if not tables:
            continue
        wd = next((i for i, d in enumerate(WEEKDAYS) if title.startswith(d)), None)
        day_idx = wd if wd is not None else day_idx + 1
        if 0 <= day_idx <= 6:
            by_day[day_idx] = tables[0]  # a repeated weekday slide: the later one stands
    for day_idx, table in sorted(by_day.items()):
        day = _day_date(meeting, day_idx)
        header = [c.text.strip() for c in table.rows[0].cells]
        for c, h in enumerate(header[1:], 1):
            lh = h.lower()
            name = "Main" if "main" in lh else "Ad hoc" if "ad hoc" in lh or "adhoc" in lh else f"BR{c - 1}"
            chair = re.findall(r"\(([^()]*?)\s*session\)", h, re.I)
            label = f"{chair[-1].strip()} session" if chair else re.sub(r"^RAN4\s*", "", h).strip() or name
            rooms[c] = _room(meeting, name, label, c - 1, main=name == "Main")
        rows: list[_Row] = []
        for r in list(table.rows)[1:]:
            cells = list(r.cells)
            t = re.sub(r"\s+", " ", cells[0].text)
            rng = re.search(rf"(\d{{1,2}})[:.](\d{{2}})\s*{D}\s*(?:(\d{{1,2}})[:.](\d{{2}})|EOM)", t, re.I)
            if not rng:
                continue
            s = _m(rng.group(1), rng.group(2))
            e = _m(rng.group(3), rng.group(4)) if rng.group(3) else None
            texts = {c: _cell_lines(cells[c]) for c in range(1, len(cells)) if not cells[c].is_spanned}
            joined = [" ".join(x for x in v if x) for v in texts.values()]
            joined = [j for j in joined if j]
            brk = None
            if joined and all(BREAK_ROW_RE.match(j) for j in joined):
                bm = BREAK_ROW_RE.match(joined[0])
                brk = "lunch" if (bm.group(1) or "").lower() == "lunch" or bm.group(3) else "coffee"
            rows.append(_Row(s, e, texts, brk))
        for i, row in enumerate(rows):
            if row.e is None and i + 1 < len(rows):
                row.e = rows[i + 1].s
            elif row.e is None:
                # "14:00-EOM": the chair gives no end; the block says so instead of a time.
                row.e = max(row.s + 60, EOM_SHOWN)
                for v in row.cells.values():
                    if any(v):
                        v.append("(until end of meeting)")
        for i, row in enumerate(rows):
            cell_base = f"{source.fileName}|{day}|{_fmt(row.s)}"
            if row.brk:
                if row.e is not None:
                    label = "Lunch" if row.brk == "lunch" else "Coffee break"
                    sessions.append(_session(meeting, rooms[1], day, row.s, row.e, [label], source,
                                             f"{cell_base}|break", kind=row.brk if row.brk == "lunch" else "break"))
                continue
            for c, lines in row.cells.items():
                if c not in rooms:
                    continue
                last_in_cell = None
                for seg in split_cell(lines):
                    span = _resolve(seg, row, rows, i)
                    if span is None:
                        problems.append(f"{day} {rooms[c].roomName} {_fmt(row.s)}: no time for {seg.lines[0]!r}")
                        continue
                    a, b = span
                    if b == a and last_in_cell is not None:
                        # "Ambient IoT (may start early)" after a part ending at the row end: no own time.
                        last_in_cell.note = " · ".join(x for x in [last_in_cell.note, *seg.lines] if x)
                        continue
                    if b <= a:
                        problems.append(f"{day} {rooms[c].roomName}: {_fmt(a)}–{_fmt(b)} ends before it starts ({seg.lines[0]!r})")
                        continue
                    if len(seg.lines) > 1 and ADHOC_RE.search(seg.lines[0]) and len(seg.lines[0]) <= 25:
                        # "Main Ad-hoc:" alone says who; the next line says what.
                        seg.lines = [f"{seg.lines[0].rstrip(': ')}: {seg.lines[1]}", *seg.lines[2:]]
                    text = " ".join(seg.lines)
                    # Ad-hoc parts (and the ad hoc room) are offline; the sessions themselves online.
                    adhoc = rooms[c].roomName == "Ad hoc" or ADHOC_RE.search(seg.lines[0]) or seg.kind
                    mode = "offline" if adhoc else "online"
                    s = _session(meeting, rooms[c], day, a, b, seg.lines, source,
                                 f"{cell_base}|{c}|{_fmt(a)}", mode=mode)
                    codes = codes_for(text, topics)
                    s.agendaItems = codes
                    s.agendaBreakdown = [AgendaSlot(code=x, label=s.topic) for x in codes]
                    s.sources = [SessionSourceRef(sourceId=source.sourceId, contributed=codes, cell=s.sources[0].cell if s.sources else None)]
                    s.derivation = "ran4-pptx"
                    sessions.append(s)
                    last_in_cell = s
    return list(rooms.values()), _trim_breaks(sessions), problems


def _trim_breaks(sessions: list[Session]) -> list[Session]:
    """An ad-hoc held during a break cuts it out of the break (both pieces stay)."""
    def m(t: str) -> int:
        return int(t[:2]) * 60 + int(t[3:])

    out: list[Session] = []
    for s in sessions:
        if s.kind == "session":
            out.append(s)
            continue
        pieces = [(m(s.startTime), m(s.endTime))]
        for o in sessions:
            if o.kind != "session" or o.roomId != s.roomId or o.date != s.date:
                continue
            oa, ob = m(o.startTime), m(o.endTime)
            pieces = [p for a, b in pieces for p in ((a, min(b, oa)), (max(a, ob), b)) if p[1] - p[0] >= 5]
        for k, (a, b) in enumerate(pieces):
            piece = copy.copy(s) if k else s
            piece.startTime, piece.endTime = _fmt(a), _fmt(b)
            if k:
                piece.sessionId = f"{s.sessionId}-{k}"
            out.append(piece)
    return out


def _resolve(seg: _Seg, row: _Row, rows: list[_Row], i: int) -> tuple[int, int] | None:
    if seg.kind:
        if seg.start is not None and seg.end is not None:
            return seg.start, seg.end
        # The neighbouring break of that kind: right after this row, else right before.
        for j in (i + 1, i - 1):
            if 0 <= j < len(rows) and rows[j].brk and rows[j].e is not None:
                if seg.kind == "lunch" and rows[j].brk != "lunch":
                    continue
                return rows[j].s, rows[j].e
        return None
    if row.e is None:
        return None
    a = seg.start if seg.start is not None else row.s
    b = seg.end if seg.end is not None else row.e
    return a, b


def build_bundle(pm: PortalMeeting, *, today: date | None = None) -> ScheduleBundle:
    from urllib.parse import unquote

    import requests

    from .live import download_to_temp

    now = datetime.now(timezone.utc)
    folder = pm.folder_url
    bis = pm.type == "bis"
    meeting = Meeting(
        id=pm.slug, slug=pm.slug, name=f"RAN4#{pm.number}{'-bis' if bis else ''}", type=pm.type,  # type: ignore[arg-type]
        startDate=pm.start_date, endDate=pm.end_date, timezone=pm.timezone,
        status=compute_status(pm.start_date, pm.end_date),  # type: ignore[arg-type]
        meetingNumber=pm.number, city=pm.city, country=pm.country,
        sources=MeetingSourceFolders(meetingFolder=folder, inbox=f"{folder}Inbox/" if folder else None,
                                     agenda=f"{folder}Agenda/" if folder else None),
        lastIngestedAt=_iso(now), workingGroup="RAN4",
    )
    phase = remote_ftp.meeting_phase(pm.start_date, pm.end_date, today)
    roots = [SYNC_ARR] + ([] if phase == "week" or not folder else [f"{folder}Inbox/Meeting_Arrangements/"])
    urls: list[str] = []
    for f in roots:
        for sub in (f, f + "History/"):
            try:
                urls += list_folder(sub)
            except Exception as exc:  # noqa: BLE001 - History is optional
                print(f"  {sub}: {exc}")
    named = [(unquote(u.rstrip("/").rsplit("/", 1)[-1]), u) for u in urls]
    s_pat, t_pat = schedule_re(pm.number, bis), topics_re(pm.number, bis)
    sched = max((nu for nu in named if s_pat.search(nu[0])), key=lambda nu: _version(s_pat, nu[0]), default=None)
    tlist = max((nu for nu in named if t_pat.search(nu[0])), key=lambda nu: _version(t_pat, nu[0]), default=None)
    print(f"  {meeting.name}: phase {phase}; schedule {sched and sched[0]}; topics {tlist and tlist[0]}")

    topics: dict[str, list[str]] = {}
    if tlist and (tp := download_to_temp(tlist[1])):
        try:
            topics = parse_topics(tp)
        except Exception as exc:  # noqa: BLE001
            print(f"  topic list unreadable: {exc}")
    rooms: list[Room] = []
    sessions: list[Session] = []
    sources: list[ScheduleSource] = []
    problems: list[str] = []
    if sched and (path := download_to_temp(sched[1])):
        src = _source(meeting, sched[1], path, "RAN4 meeting schedule", "main_schedule", now)
        rooms, sessions, problems = parse_schedule(path, meeting, src, topics)
        sources.append(src)
    agenda: list[AgendaItem] = []
    for a_url in [f"{folder}Agenda/agenda.csv"] if folder else []:
        try:
            from .http_cache import cached_get

            body = cached_get(a_url, timeout=30)
            if body and body.strip():
                agenda = parse_agenda_csv(body.decode("utf-8", "replace"), meeting.id)
        except Exception:  # noqa: BLE001
            pass
    used = {s.roomId for s in sessions}
    rooms = [r for r in rooms if r.roomId in used]
    problems += overlap_problems(sessions)
    PROBLEMS[meeting.id] = problems
    sessions.sort(key=lambda s: (s.date, s.startTime, s.roomId))
    meeting.schedulePublished = bool(sessions)
    return ScheduleBundle(
        generatedAt=_iso(now), meeting=meeting, rooms=rooms, sessions=sessions,
        agendaItems=agenda, sources=sources, topics=topics or None,
        ingest=IngestStatus(state="ok", lastSuccessfulAt=_iso(now), lastAttemptAt=_iso(now),
                            message=None if sessions else "No RAN4 meeting schedule published yet."),
    )
