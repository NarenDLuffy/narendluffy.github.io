"""SA1 schedule: the chair's Q0–Q5 week grid.

* Source: Meetings_3GPP_SYNC/SA1/Inbox/agenda — "Breakout sessions schedule_SA1#<n>"
  and the chair's "Agenda for SA1#<n>[_DAY_hh_mm]" (its weekday table). Both name
  the meeting; the file Word last saved (docProps/core.xml) wins.
* Rooms come from the "MEETING ROOMS:" lines: "Plenary/ Breakout 1: <room>" is the
  main lane, "Breakout 2: <room>" the second. In a cell, "Plenary:"/"Breakout 1:"
  open the main lane, "Breakout 2:" the second; "=====" separates them.
* Each quarter is one block per lane. A line that is only a time "(19:15-20:30)"
  gives the line above it its own block at that time; "hh:mm till hh:mm …" in a
  break row is timed; "Meeting ends 16:00" ends the block. Break rows ("Coffee",
  "Lunch") span the gap between neighbouring quarters. Nothing else is timed.
* Agenda codes only where a line starts with a number ("7.4.3 AI", "1. Opening")
  or after "+" ("7.4.10 IMS+7.4.6 Immersive"); titles come from those same lines.
"""

from __future__ import annotations

import re
import zipfile
from datetime import date, datetime, timezone

from .docx_active_text import active_element_text
from .meeting_discovery import compute_status
from .models import AgendaItem, AgendaSlot, IngestStatus, Meeting, MeetingSourceFolders, Room, ScheduleBundle, ScheduleSource, Session
from .portal import PortalMeeting, list_folder
from .ran2_schedule import PROBLEMS, WEEKDAYS, _day_date, _grid_rows, _iso, _key
from .ran3_schedule import _fmt, _room, _session, _source, overlap_problems
from .ranp_schedule import _trim_breaks

SYNC_AGENDA = "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/SA1/Inbox/agenda/"
T = r"(\d{1,2})[:.](\d{2})"
RANGE_RE = re.compile(rf"{T}\s*(?:[-–—~]|till|to)\s*{T}", re.I)
ONLY_RANGE_RE = re.compile(rf"^\(?\s*{T}\s*[-–—~]\s*{T}\s*\)?$")
LANE_RE = re.compile(r"^\s*(plenary|breakout\s*(\d))\s*:?\s*(.*)$", re.I)
CODE_RE = re.compile(r"(?:^|\+)\s*(\d+(?:\.\d+)*)\.?(?=\s|$|[A-Za-z])")


def file_re(number: int) -> re.Pattern[str]:
    return re.compile(rf"(breakout\s*sessions?\s*schedule|agenda\s*for)[ _]*SA1\s*#\s*{number}(?!\d).*\.docx$", re.I)


def saved_at(path: str) -> str:
    try:
        x = zipfile.ZipFile(path).read("docProps/core.xml").decode("utf-8", "replace")
        m = re.search(r"<dcterms:modified[^>]*>([^<]+)<", x)
        return m.group(1) if m else ""
    except Exception:  # noqa: BLE001
        return ""


def sa1_codes(lines: list[str]) -> list[str]:
    out = []
    for l in lines:
        for m in CODE_RE.finditer(l.strip()):
            out.append(m.group(1))
    return list(dict.fromkeys(out))


def _hm(h, m) -> int:
    return int(h) * 60 + int(m)


def room_names(doc) -> dict[str, str]:
    out = {}
    for p in doc.paragraphs[:20]:
        t = re.sub(r"\s+", " ", active_element_text(p._p)).strip()
        m = re.match(r"^(plenary\s*/\s*breakout\s*1|plenary|breakout\s*1)\s*:\s*(.+)$", t, re.I)
        if m:
            out.setdefault("a", m.group(2))
        m = re.match(r"^breakout\s*2\s*:\s*(.+)$", t, re.I)
        if m:
            out["b"] = m.group(1)
    return out


def _lanes(text: str):
    """Cell text -> [(lane, lines, window)] in order; a lone time line splits off the line above."""
    blocks: list[list] = []
    lane = "a"
    cur = None
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line or re.fullmatch(r"=+", line):
            continue
        m = LANE_RE.match(line)
        if m:
            lane = "b" if (m.group(2) or "") == "2" else "a"
            cur = [lane, [], None]
            blocks.append(cur)
            line = m.group(3).strip()
            if not line:
                continue
        if cur is None or cur[0] != lane:
            cur = [lane, [], None]
            blocks.append(cur)
        r = ONLY_RANGE_RE.match(line)
        if r and cur[1]:
            prev = cur[1].pop()
            blocks.append([lane, [prev], (_hm(*r.groups()[:2]), _hm(*r.groups()[2:]))])
            continue
        if re.match(r"^\(?start at\b", line, re.I):
            continue
        cur[1].append(line)
    return [(l, ls, w) for l, ls, w in blocks if ls]


def parse_grid(path: str, meeting: Meeting, source: ScheduleSource):
    import docx

    doc = docx.Document(path)
    table = next((t for t in doc.tables if re.search(r"\bQ1\b", active_element_text(t._tbl))
                  and sum(d in active_element_text(t._tbl).lower() for d in WEEKDAYS[:5]) >= 3), None)
    if table is None:
        return [], [], ["SA1 grid: no Q1–Q5 weekday table found"]
    names = room_names(doc)
    rooms = {"a": _room(meeting, "Plenary / Breakout 1", names.get("a", "SA1 Plenary"), 0, main=True),
             "b": _room(meeting, "Breakout 2", names.get("b", "SA1 Breakout 2"), 1)}
    rows = [[(c, tc, mg, active_element_text(tc)) for c, tc, mg in r] for r in _grid_rows(table)]
    days: dict[int, str] = {}
    for c, _tc, _mg, t in rows[0]:
        wd = next((i for i, d in enumerate(WEEKDAYS) if t.strip().lower().startswith(d)), None)
        if wd is not None:
            days[c] = _day_date(meeting, wd)
    quarters = []
    for r in rows:
        lab = " ".join(x[3] for x in r[:2])
        m = re.search(rf"{T}\s*\W*\s*{T}", lab)
        quarters.append((_hm(*m.groups()[:2]), _hm(*m.groups()[2:])) if m and re.search(r"\bQ\d", lab) else None)
    sessions: list[Session] = []
    problems: list[str] = []
    for ri, r in enumerate(rows[1:], 1):
        lab = " ".join(x[3] for x in r[:2]).lower()
        brk = re.search(r"\b(coffee|lunch)\b", lab)
        if quarters[ri]:
            s0, e0 = quarters[ri]
        elif brk:
            prev = next((q for q in reversed(quarters[:ri]) if q), None)
            nxt = next((q for q in quarters[ri + 1:] if q), None)
            if not prev or not nxt or nxt[0] <= prev[1]:
                continue
            s0, e0 = prev[1], nxt[0]
        else:
            continue
        for c, day in days.items():
            cell = next((x for x in r if x[0] == c), None)
            cid = f"{source.fileName}|grid|{day}|{_fmt(s0)}-{_fmt(e0)}|c{c}"
            if brk:
                sessions.append(_session(meeting, rooms["a"], day, s0, e0, ["Lunch" if brk.group(1) == "lunch" else "Coffee break"],
                                         source, cid, kind="lunch" if brk.group(1) == "lunch" else "break"))
            if cell is None or cell[2] == "continue" or not cell[3].strip():
                continue
            for lane, lines, win in _lanes(cell[3]):
                s, e = s0, e0
                if win:
                    s, e = win
                if brk:
                    rg = RANGE_RE.search(" ".join(lines))
                    if not rg:
                        continue  # nothing timed during the break
                    s, e = _hm(*rg.groups()[:2]), _hm(*rg.groups()[2:])
                    lines = [RANGE_RE.sub("", lines[0]).strip()] + lines[1:]
                end = re.search(rf"meeting ends\s*{T}", " ".join(lines), re.I)
                if end:
                    e = min(e, _hm(*end.groups()))
                    lines = [l for l in lines if not re.match(r"meeting ends", l, re.I)]
                if not lines or e <= s:
                    continue
                sess = _session(meeting, rooms[lane], day, s, e, lines, source, f"{cid}|{lane}|{_fmt(s)}")
                codes = sa1_codes(lines)
                sess.agendaItems = codes
                sess.agendaBreakdown = [AgendaSlot(code=c, label=sess.topic) for c in codes]
                if sess.sources:
                    sess.sources[0].contributed = codes
                sessions.append(sess)
    # A timed item after the quarter (MMS 19:15–20:30) shortens nothing else; one inside it trims the lane block.
    def mins(t):
        return int(t[:2]) * 60 + int(t[3:])
    for s in sessions:
        for o in sessions:
            if o is not s and o.kind == s.kind == "session" and o.roomId == s.roomId and o.date == s.date \
                    and mins(s.startTime) < mins(o.startTime) < mins(s.endTime):
                s.endTime = o.startTime
    # A break holding a timed item (newcomers' talk 12:45–13:45) gives way to it; a break
    # with nothing after it that day (Friday after the meeting ends) is dropped.
    def inside(b, o):
        return o.kind == "session" and o.roomId == b.roomId and o.date == b.date \
            and mins(b.startTime) < mins(o.startTime) and mins(o.endTime) < mins(b.endTime)
    sessions = [b for b in sessions if b.kind == "session" or (
        not any(inside(b, o) for o in sessions)
        and any(o.kind == "session" and o.date == b.date and mins(o.startTime) >= mins(b.endTime) for o in sessions))]
    return list(rooms.values()), _trim_breaks(sessions), problems


def agenda_from(sessions: list[Session], meeting_id: str) -> list[AgendaItem]:
    items: dict[str, AgendaItem] = {}
    for s in sessions:
        for line in [s.topic] + (s.note or "").split(" · "):
            for part in line.split("+"):
                m = re.match(r"^\s*(\d+(?:\.\d+)*)\.?\s+(.+)$", part.strip())
                if m and m.group(1) not in items:
                    code = m.group(1)
                    items[code] = AgendaItem(code=code, meetingId=meeting_id, title=m.group(2).strip(),
                                             parent=code.rsplit(".", 1)[0] if "." in code else None,
                                             topicKey=_key(m.group(2).lower())[:8])
    return sorted(items.values(), key=lambda a: [int(x) for x in a.code.split(".")])


def build_bundle(pm: PortalMeeting, *, today: date | None = None) -> ScheduleBundle:
    from urllib.parse import unquote

    from .live import download_to_temp

    now = datetime.now(timezone.utc)
    folder = pm.folder_url
    meeting = Meeting(
        id=pm.slug, slug=pm.slug, name=pm.name, type=pm.type,  # type: ignore[arg-type]
        startDate=pm.start_date, endDate=pm.end_date, timezone=pm.timezone,
        status=compute_status(pm.start_date, pm.end_date),  # type: ignore[arg-type]
        meetingNumber=pm.number, city=pm.city, country=pm.country,
        sources=MeetingSourceFolders(meetingFolder=folder, inbox=None, agenda=SYNC_AGENDA),
        lastIngestedAt=_iso(now), workingGroup="SA1",
    )
    try:
        urls = list_folder(SYNC_AGENDA)
    except Exception as exc:  # noqa: BLE001
        print(f"  {SYNC_AGENDA}: {exc}")
        urls = []
    pat = file_re(pm.number)
    hits = [u for u in urls if pat.search(unquote(u.rsplit("/", 1)[-1]))]
    best = None
    for u in hits:
        path = download_to_temp(u)
        if path and (best is None or saved_at(path) > best[2]):
            best = (u, path, saved_at(path))
    print(f"  {meeting.name}: SA1 grid {best[0] if best else 'none'}")
    rooms: list[Room] = []
    sessions: list[Session] = []
    sources: list[ScheduleSource] = []
    problems: list[str] = []
    if best:
        src = _source(meeting, best[0], best[1], "SA1 chair schedule", "main_schedule", now)
        src.revision = best[2] or None
        rooms, sessions, problems = parse_grid(best[1], meeting, src)
        sources.append(src)
    agenda = agenda_from(sessions, meeting.id)
    used = {s.roomId for s in sessions}
    rooms = [r for r in rooms if r.roomId in used]
    problems += overlap_problems(sessions)
    PROBLEMS[meeting.id] = problems
    sessions.sort(key=lambda s: (s.date, s.startTime, s.roomId))
    meeting.schedulePublished = bool(sessions)
    return ScheduleBundle(
        generatedAt=_iso(now), meeting=meeting, rooms=rooms, sessions=sessions,
        agendaItems=agenda, sources=sources,
        ingest=IngestStatus(state="ok", lastSuccessfulAt=_iso(now), lastAttemptAt=_iso(now),
                            message=None if sessions else "No SA1 schedule published yet."),
    )
