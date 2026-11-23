"""SA2 schedule: the convenors' "S2-xxxxxxx_SA2-<n>-Session Plan - rNN" DOCX.

* Source: Meetings_3GPP_SYNC/SA2/Inbox/Drafts/_Session_Plan_Updates (+ _OLDER) and
  the meeting's own Inbox/Drafts/_Session_Plan_Updates; names carry "SA2-<n>", so
  Sync is always read. Highest rNN wins (docx or zip).
* Room table: "Main Room | <name> | Breakout 1 | <name> | Breakout 2 | <name>".
* Plan table: weekdays across (two columns per day), "Q1 | 0900 - 1030 | Stream N"
  rows down. Stream 1 sits in Main, Stream 2 in Breakout 1, Stream 3 in Breakout 2,
  unless the cell starts "In breakout 1" / "In main room".
* The two columns of a day are one quarter: items from both are listed, never
  split at an invented half-time. Coffee/Lunch rows have no written time — they
  span the gap between neighbouring quarters; "Main:13:00 …" during lunch starts
  at the written time. A written "(1330 - 1600)" in a cell sets that block's time.
* Agenda codes only from written numbers: "(20.6.18)", "(20.6.12 – 16)", "(4.1)",
  "20.48, 20.49"; ".x" means the parent; "[9]" is a tdoc count, not a code.
Shared rules (ingestion/AGENTS.md): active Word text only, never invent times,
overlaps refuse the publish.
"""

from __future__ import annotations

import re
import zipfile
from datetime import date, datetime, timezone

import ingestion.remote_ftp as remote_ftp

from .docx_active_text import active_element_text
from .meeting_discovery import compute_status
from .models import AgendaItem, IngestStatus, Meeting, MeetingSourceFolders, Room, ScheduleBundle, ScheduleSource, Session
from .portal import PortalMeeting, list_folder
from .ran2_schedule import PROBLEMS, WEEKDAYS, _day_date, _grid_rows, _iso
from .ran3_schedule import _fmt, _room, _session, _source, overlap_problems
from .ranp_schedule import _trim_breaks, parse_agenda_csv

SYNC_PLANS = "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/SA2/Inbox/Drafts/_Session_Plan_Updates/"
SYNC_AGENDA = "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/SA2/Agenda/"
QRANGE_RE = re.compile(r"\b(\d{1,2})[:.]?(\d{2})\s*[-–—~]\s*(\d{1,2})[:.]?(\d{2})\b")
START_RE = re.compile(r"^\s*(main|breakout\s*\d)?\s*:?\s*(\d{1,2})[:.](\d{2})\s*:?\s*", re.I)
REDIRECT_RE = re.compile(r"^\s*in\s+(main\s+room|breakout\s*(\d))\s*$", re.I)
SKIP_RE = re.compile(r"^\s*(opening|close)\s+of\s+meeting\b", re.I)
PAREN_RE = re.compile(r"\((\d+(?:\.\d+)*(?:\.x)?)(?:\s*[–—-]\s*(\d+))?\)", re.I)
BARE_RE = re.compile(r"(?<![\d.#])(\d{1,2}\.\d+(?:\.\d+)*)(?![\d.])")


def plan_re(number: int) -> re.Pattern[str]:
    return re.compile(rf"SA2[-#_ ]?{number}[-_ ]+Session\s*Plan(?:\s*-\s*r(\d+))?\.(docx|zip)$", re.I)


def plan_rank(name: str) -> tuple:
    m = re.search(r"r(\d+)\.(?:docx|zip)$", name, re.I)
    return (int(m.group(1)) if m else -1, name.lower().endswith(".docx"))


def sa2_codes(text: str) -> list[str]:
    """Written agenda numbers only; tdoc counts "[9]" and KI numbers are ignored."""
    text = re.sub(r"\[[^\]\n]*\]", " ", text)
    out: list[str] = []
    for m in PAREN_RE.finditer(text):
        code = re.sub(r"\.x$", "", m.group(1), flags=re.I)
        if m.group(2) and "." in code:
            head, first = code.rsplit(".", 1)
            if int(first) < int(m.group(2)) <= int(first) + 20:
                out += [f"{head}.{i}" for i in range(int(first), int(m.group(2)) + 1)]
                continue
        out.append(code)
    for m in BARE_RE.finditer(PAREN_RE.sub(" ", text)):
        out.append(m.group(1))
    return list(dict.fromkeys(out))


def _session_sa2(meeting, room, day, s, e, lines, source, cell, kind="session"):
    sess = _session(meeting, room, day, s, e, lines, source, cell, kind=kind)
    codes = sa2_codes("\n".join(lines))
    sess.agendaItems = codes
    from .models import AgendaSlot

    sess.agendaBreakdown = [AgendaSlot(code=c, label=sess.topic) for c in codes]
    if sess.sources:
        sess.sources[0].contributed = codes
    return sess


def _hm(h: str, m: str) -> int:
    return int(h) * 60 + int(m)


def room_names(doc) -> dict[str, str]:
    """{"main": "Palomino E-H (300)", "breakout1": ..., "breakout2": ...} from the room table."""
    out: dict[str, str] = {}
    for t in doc.tables:
        for r in t.rows:
            cells = [active_element_text(c._tc).strip() for c in r.cells]
            for a, b in zip(cells, cells[1:]):
                k = re.sub(r"\s+", "", a.lower())
                if k in ("mainroom", "breakout1", "breakout2", "breakout3") and b:
                    out[k.replace("room", "")] = re.sub(r"\s+", " ", b)
    return out


def _clean(lines: list[str]) -> list[str]:
    out = []
    for l in lines:
        l = re.sub(r"\s+", " ", l).strip(" /")
        if not l or re.fullmatch(r"drafting\s*:?", l, re.I):
            continue
        out.append(l)
    return list(dict.fromkeys(out))


def parse_session_plan(path: str, meeting: Meeting, source: ScheduleSource):
    import docx

    doc = docx.Document(path)
    table = next((t for t in doc.tables if "stream" in active_element_text(t._tbl).lower()
                  and sum(d in active_element_text(t._tbl).lower() for d in WEEKDAYS[:5]) >= 3), None)
    if table is None:
        return [], [], ["session plan: no weekday/stream table found"]
    names = room_names(doc)
    rooms = {
        "main": _room(meeting, "Main", names.get("main", "SA2 Main"), 0, main=True),
        "breakout1": _room(meeting, "Breakout 1", names.get("breakout1", "SA2 Breakout 1"), 1),
        "breakout2": _room(meeting, "Breakout 2", names.get("breakout2", "SA2 Breakout 2"), 2),
    }
    stream_room = {"1": "main", "2": "breakout1", "3": "breakout2"}
    rows = [[(c, tc, mg, active_element_text(tc)) for c, tc, mg in r] for r in _grid_rows(table)]
    header = next(r for r in rows if sum(any(x[3].strip().lower().startswith(d) for d in WEEKDAYS[:5]) for x in r) >= 3)
    days: dict[str, list[int]] = {}
    for c, _tc, _mg, t in header:
        wd = next((i for i, d in enumerate(WEEKDAYS) if t.strip().lower().startswith(d)), None)
        if wd is not None:
            days.setdefault(_day_date(meeting, wd), []).append(c)
    # A day heading may span both of its columns: a day owns every column up to the next day.
    starts = sorted((min(cs), d) for d, cs in days.items())
    last_col = max(c for r in rows for c, *_ in r)
    days = {d: list(range(c0, starts[i + 1][0] if i + 1 < len(starts) else last_col + 1))
            for i, (c0, d) in enumerate(starts)}

    def label(r):
        return re.sub(r"\s+", " ", " ".join(x[3] for x in r[:3])).strip()

    # Quarter ranges in row order; break rows take the gap between neighbours.
    quarters: list[tuple[int, int] | None] = []
    cur = None
    for r in rows:
        m = QRANGE_RE.search(label(r))
        if m and re.search(r"\bQ\d\b", r[0][3]):
            cur = (_hm(*m.groups()[:2]), _hm(*m.groups()[2:]))
        quarters.append(cur)
    q_starts = sorted({q for q in quarters if q})

    sessions: list[Session] = []
    problems: list[str] = []
    for ri, r in enumerate(rows):
        q = quarters[ri]
        if q is None:
            continue
        lab = label(r).lower()
        sm = re.search(r"stream\s*(\d)", lab)
        brk = re.search(r"\b(coffee|lunch|break)\b", lab)
        if not sm and not brk:
            continue
        if brk:
            nxt = next((x for x in q_starts if x[0] >= q[1]), None)
            if nxt is None or nxt[0] <= q[1]:
                continue
            s0, e0 = q[1], nxt[0]
        else:
            s0, e0 = q
        for day, cols in days.items():
            cells = [x for x in r if x[0] in cols and x[2] != "continue"]
            seen, lines, target = set(), [], None
            window = None
            for _c, tc, _mg, text in cells:
                if id(tc) in seen:
                    continue
                seen.add(id(tc))
                for raw in text.splitlines():
                    if SKIP_RE.match(raw):
                        continue
                    rd = REDIRECT_RE.match(raw)
                    if rd:
                        target = target or ("main" if rd.group(1).lower().startswith("main") else f"breakout{rd.group(2)}")
                        continue
                    if not lines:
                        w = QRANGE_RE.search(raw)
                        if w and re.search(r"\(\s*\d{3,4}\s*-\s*\d{3,4}\s*\)", raw):
                            window = (_hm(*w.groups()[:2]), _hm(*w.groups()[2:]))
                            raw = QRANGE_RE.sub("", raw).replace("()", "")
                        st = START_RE.match(raw)
                        if st and brk:
                            window = (_hm(st.group(2), st.group(3)), e0)
                            target = target or ("main" if (st.group(1) or "main").lower() == "main" else None)
                            raw = raw[st.end():]
                    lines.append(raw)
            lines = _clean(lines)
            cell_id = f"{source.fileName}|plan|{day}|{_fmt(s0)}-{_fmt(e0)}|r{ri}"
            if brk:
                kind = "lunch" if brk.group(1) == "lunch" else "break"
                if day not in [s.date for s in sessions if s.startTime == _fmt(s0) and s.kind in ("lunch", "break")]:
                    sessions.append(_session_sa2(meeting, rooms["main"], day, s0, e0,
                                                 ["Lunch" if kind == "lunch" else "Coffee break"], source, cell_id, kind=kind))
            if not lines:
                continue
            room_key = target or (stream_room.get(sm.group(1), "main") if sm else "main")
            if room_key not in rooms:
                problems.append(f"session plan {day} {_fmt(s0)}: unknown room {room_key!r}")
                continue
            s, e = window if window and window[0] < window[1] else (s0, e0)
            sessions.append(_session_sa2(meeting, rooms[room_key], day, s, e, lines, source,
                                         f"{cell_id}|{room_key}"))
    # A written plenary window ("(1330 - 1600)") replaces the quarters it covers;
    # breaks are trimmed around it, and a break with no session after it that day is dropped.
    def mins(t):
        return int(t[:2]) * 60 + int(t[3:])
    wide = [s for s in sessions if s.kind == "session" and (mins(s.endTime) - mins(s.startTime)) > 120]
    for s in sessions:  # a lunch-time item running into the plenary ends where it starts
        for w in wide:
            if s is not w and s.kind == "session" and w.date == s.date and mins(s.startTime) < mins(w.startTime) < mins(s.endTime):
                s.endTime = w.startTime
    sessions = [s for s in sessions if s in wide or s.kind in ("break", "lunch") or not any(
        w.date == s.date and mins(w.startTime) <= mins(s.startTime) < mins(w.endTime) for w in wide)]
    sessions = [s for s in sessions if s.kind == "session" or (
        any(o.kind == "session" and o.date == s.date and mins(o.endTime) <= mins(s.startTime) for o in sessions)
        and any(o.kind == "session" and o.date == s.date and mins(o.startTime) > mins(s.startTime) for o in sessions))]
    return list(rooms.values()), _trim_breaks(sessions), problems


def _docx_from(path: str) -> str | None:
    if path.lower().endswith(".docx") or not zipfile.is_zipfile(path):
        return path
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".docx")]
        if not names:
            return None
        out = path + ".docx"
        with open(out, "wb") as f:
            f.write(z.read(sorted(names)[-1]))
        return out


def build_bundle(pm: PortalMeeting, *, today: date | None = None) -> ScheduleBundle:
    from urllib.parse import unquote

    from .http_cache import cached_get
    from .live import download_to_temp

    now = datetime.now(timezone.utc)
    folder = pm.folder_url
    meeting = Meeting(
        id=pm.slug, slug=pm.slug, name=pm.name, type=pm.type,  # type: ignore[arg-type]
        startDate=pm.start_date, endDate=pm.end_date, timezone=pm.timezone,
        status=compute_status(pm.start_date, pm.end_date),  # type: ignore[arg-type]
        meetingNumber=pm.number, city=pm.city, country=pm.country,
        sources=MeetingSourceFolders(meetingFolder=folder, inbox=f"{folder}Inbox/" if folder else None,
                                     agenda=f"{folder}Agenda/" if folder else None),
        lastIngestedAt=_iso(now), workingGroup="SA2",
    )
    phase = remote_ftp.meeting_phase(pm.start_date, pm.end_date, today)
    roots = [SYNC_PLANS] + ([f"{folder}Inbox/Drafts/_Session_Plan_Updates/", f"{folder}Agenda/"]
                            if folder and phase != "week" else [])
    urls: list[str] = []
    for f in roots + [r + "_OLDER/" for r in roots if r.endswith("Updates/")]:
        try:
            urls += list_folder(f)
        except Exception as exc:  # noqa: BLE001 - a missing folder is normal
            print(f"  {f}: {exc}")
    pat = plan_re(pm.number)
    hits = [(unquote(u.rstrip("/").rsplit("/", 1)[-1]), u) for u in urls]
    hits = [(n, u) for n, u in hits if pat.search(n)]
    plan_url = max(hits, key=lambda nu: plan_rank(nu[0]))[1] if hits else None
    print(f"  {meeting.name}: phase {phase}; session plan {plan_url or 'none'}")
    rooms: list[Room] = []
    sessions: list[Session] = []
    sources: list[ScheduleSource] = []
    problems: list[str] = []
    if plan_url and (raw := download_to_temp(plan_url)) and (path := _docx_from(raw)):
        src = _source(meeting, plan_url, path, "SA2 session plan", "main_schedule", now)
        m = re.search(r"r(\d+)\.(?:docx|zip)$", src.fileName, re.I)
        if m:
            src.revision, src.revisionParts = f"r{m.group(1)}", [int(m.group(1))]
        rooms, sessions, problems = parse_session_plan(path, meeting, src)
        sources.append(src)
    agenda: list[AgendaItem] = []
    for a_url in ([f"{folder}Agenda/agenda.csv"] if folder else []) + ([SYNC_AGENDA + "agenda.csv"] if phase in ("week", "edge") else []):
        try:
            body = cached_get(a_url, timeout=30)
            if body and body.strip():
                agenda = parse_agenda_csv(body.decode("utf-8", "replace"), meeting.id)
                if agenda:
                    break
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
        agendaItems=agenda, sources=sources,
        ingest=IngestStatus(state="ok", lastSuccessfulAt=_iso(now), lastAttemptAt=_iso(now),
                            message=None if sessions else "No SA2 session plan published yet."),
    )
