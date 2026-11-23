"""RAN Plenary (TSG RAN) schedule: the chair's "RAN#<n> time plan vNN" DOCX.

* Source: Meetings_3GPP_SYNC/RAN/Inbox/Chair (meeting days) or the meeting's
  own Inbox/Chair; the file is often zipped. Highest version wins.
* The time-plan table: weekdays across, "08:00 ~ 09:00" rows down. A row whose
  cells all say "... BREAK" is a break; the row right after it with the same
  time holds meetings during that break.
* Lanes inside a cell: lines starting "Main" go to Main, "Breakout" to the
  breakout room; continuation lines follow the open lane; plain text is the
  plenary itself (Main). An inline "(12:30~13:30)" narrows that lane's time;
  "in RAN main room" forces Main. "TBD" lines carry nothing and are skipped.
* Agenda codes only from written "AI x" numbers; titles from agenda.csv.
Shared rules (ingestion/AGENTS.md): active Word text only, never invent times,
overlaps refuse the publish, an older version never replaces a newer build.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from datetime import date, datetime, timezone

import ingestion.remote_ftp as remote_ftp

from .docx_active_text import active_element_text
from .meeting_discovery import compute_status
from .models import (
    AgendaItem,
    IngestStatus,
    Meeting,
    MeetingSourceFolders,
    Room,
    ScheduleBundle,
    ScheduleSource,
    Session,
)
from .portal import PortalMeeting, list_folder
from .ran2_schedule import PROBLEMS, WEEKDAYS, _day_date, _grid_rows, _iso, _key
from .ran3_schedule import _fmt, _room, _session, _source, overlap_problems

SYNC_CHAIR = "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN/Inbox/Chair/"
SYNC_AGENDA = "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN/Agenda/"
RANGE_RE = re.compile(r"(\d{1,2})[:.](\d{2})\s*[~–—-]\s*(\d{1,2})[:.](\d{2})")
LANE_RE = re.compile(r"^\s*(main|breakout)\b\s*(\([^)]*\))?\s*:?\s*(.*)$", re.I)
BREAK_RE = re.compile(r"\b(coffee|lunch)\s+break\b", re.I)


def time_plan_re(number: int) -> re.Pattern[str]:
    return re.compile(rf"^RAN\s*#\s*{number}\s+time\s*plan\s*v(\d+)\.(docx|zip)$", re.I)


def plan_rank(name: str) -> tuple:
    m = re.search(r"v(\d+)\.(?:docx|zip)$", name, re.I)
    return (int(m.group(1)) if m else -1, name.lower().endswith(".docx"))


def candidate_folders(meeting_folder: str | None, phase: str) -> list[str]:
    """Sync Chair is always read: every time-plan name carries its meeting number,
    so the previous meeting's plan can never be taken for this one."""
    own = [meeting_folder + "Inbox/Chair/"] if meeting_folder else []
    return [SYNC_CHAIR] + ([] if phase == "week" else own)


def _mins(h: str, m: str) -> int:
    return int(h) * 60 + int(m)


def _lanes(text: str) -> dict[str, list[tuple[str, tuple[int, int] | None]]]:
    """Cell text -> {"main": [(line, window)], "breakout": [...]}; window from an inline time."""
    out: dict[str, list[tuple[str, tuple[int, int] | None]]] = {"main": [], "breakout": []}
    lane = None
    window: tuple[int, int] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = LANE_RE.match(line)
        if m:
            lane = m.group(1).lower()
            rng = RANGE_RE.search(m.group(2) or "")
            window = (_mins(*rng.groups()[:2]), _mins(*rng.groups()[2:])) if rng else None
            line = m.group(3).strip()
            if not line:
                continue
        target = lane or "main"
        rng = RANGE_RE.search(line)
        win = window
        if rng and lane is None:
            win = (_mins(*rng.groups()[:2]), _mins(*rng.groups()[2:]))
        if re.search(r"in RAN main room", line, re.I):
            target = "main"
        line = re.sub(r"\s*\((?:\d{1,2}[:.]\d{2}\s*[~–—-]\s*\d{1,2}[:.]\d{2})?\s*(?:in RAN main room)?\)", "", line, flags=re.I).strip()
        if not line or re.fullmatch(r"TBD\.?", line, re.I):
            continue
        out[target].append((line, win))
    return out


def room_labels(doc) -> tuple[str, str]:
    """("Madrid 3/4/5/6", "Madrid 1-2 (until Tue AM), Neptuno + PTA Alcala (from Tue PM)") from the heading line."""
    for p in doc.paragraphs[:15]:
        t = active_element_text(p._p)
        m = re.search(r"Main:\s*(.+?),\s*Breakout:\s*(.+)$", t)
        if m:
            return m.group(1).strip(), m.group(2).strip()
    return "", ""


def parse_time_plan(path: str, meeting: Meeting, source: ScheduleSource):
    import docx

    doc = docx.Document(path)
    table = next((t for t in doc.tables
                  if sum(d in active_element_text(t._tbl).lower() for d in WEEKDAYS[:5]) >= 2), None)
    if table is None:
        return [], [], ["time plan: no weekday table found"]
    main_label, brk_label = room_labels(doc)
    main = _room(meeting, "Main", main_label or "RAN Plenary", 0, main=True)
    brk = _room(meeting, "Breakout", brk_label or "RAN Plenary", 1)
    rows = [[(c, tc, mg, active_element_text(tc)) for c, tc, mg in r] for r in _grid_rows(table)]
    days: dict[int, str] = {}
    for c, _tc, _mg, t in rows[0]:
        wd = next((i for i, d in enumerate(WEEKDAYS) if t.strip().lower().startswith(d)), None)
        if wd is not None:
            days[c] = _day_date(meeting, wd)
    sessions: list[Session] = []
    problems: list[str] = []
    last_range: tuple[int, int] | None = None
    for ri, r in enumerate(rows[1:], 1):
        rng = RANGE_RE.search(re.sub(r"\s+", " ", r[0][3]))
        if rng:
            s0, e0 = _mins(*rng.groups()[:2]), _mins(*rng.groups()[2:])
        elif r[0][2] == "continue" and last_range:
            s0, e0 = last_range  # second row under a merged time cell: meetings during the break
        else:
            continue
        last_range = (s0, e0)
        # A break written once across the whole row applies to every day.
        row_text = [x[3] for x in r[1:] if x[3].strip()]
        whole_break = bool(row_text) and all(BREAK_RE.search(t) and len(t.strip()) < 40 for t in row_text)
        if e0 <= s0:
            problems.append(f"time plan row {ri}: end before start ({r[0][3]!r})")
            continue
        for c, day in days.items():
            cell = next((x for x in r if x[0] == c), None)
            if whole_break and (cell is None or not cell[3].strip()):
                cell = (c, None, None, row_text[0])
            if cell is None or cell[2] == "continue" or not cell[3].strip():
                continue
            text = cell[3]
            cell_id = f"{source.fileName}|plan|{day}|{_fmt(s0)}-{_fmt(e0)}|{c}"
            b = BREAK_RE.search(text)
            if b and len(text.strip()) < 40:
                kind = "lunch" if b.group(1).lower() == "lunch" else "break"
                sessions.append(_session(meeting, main, day, s0, e0, ["Lunch" if kind == "lunch" else "Coffee break"],
                                         source, cell_id, kind=kind))
                continue
            for lane, room in (("main", main), ("breakout", brk)):
                items = _lanes(text)[lane]
                if not items:
                    continue
                win = next((w for _l, w in items if w), None)
                s, e = win if win and s0 <= win[0] < win[1] <= e0 else (s0, e0)
                sessions.append(_session(meeting, room, day, s, e, [l for l, _w in items], source,
                                         f"{cell_id}|{lane}", mode="online" if lane == "main" else "offline"))
    return [main, brk], _trim_breaks(sessions), problems


def _trim_breaks(sessions: list[Session]) -> list[Session]:
    """A meeting held during a break shortens that break; the break is never stacked under it."""
    def m(t: str) -> int:
        return int(t[:2]) * 60 + int(t[3:])

    out: list[Session] = []
    for s in sessions:
        if s.kind not in ("break", "lunch"):
            out.append(s)
            continue
        a, b = m(s.startTime), m(s.endTime)
        for o in sessions:
            if o.kind != "session" or o.roomId != s.roomId or o.date != s.date:
                continue
            oa, ob = m(o.startTime), m(o.endTime)
            if oa <= a < ob:
                a = ob
            if oa < b <= ob:
                b = oa
        if b > a:
            s.startTime, s.endTime = _fmt(a), _fmt(b)
            out.append(s)
    return out


def parse_agenda_csv(text: str, meeting_id: str) -> list[AgendaItem]:
    items: list[AgendaItem] = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 2 or not re.fullmatch(r"\d+(?:\.\d+)*", row[0].strip()):
            continue
        code, title = row[0].strip(), row[1].strip()
        items.append(AgendaItem(code=code, meetingId=meeting_id, title=title,
                                parent=code.rsplit(".", 1)[0] if "." in code else None,
                                topicKey=_key(title.lower())[:8]))
    return items


def _docx_from(path: str, number: int) -> str | None:
    if path.lower().endswith(".docx") or not zipfile.is_zipfile(path):
        return path
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".docx") and f"#{number}" in n.replace(" ", "")]
        names = names or [n for n in z.namelist() if n.lower().endswith(".docx")]
        if not names:
            return None
        out = path + ".docx"
        with open(out, "wb") as f:
            f.write(z.read(names[0]))
        return out


def build_bundle(pm: PortalMeeting, *, today: date | None = None) -> ScheduleBundle:
    from urllib.parse import unquote

    import requests

    from .live import download_to_temp

    now = datetime.now(timezone.utc)
    folder = pm.folder_url
    meeting = Meeting(
        id=pm.slug, slug=pm.slug, name=f"RAN#{pm.number}", type=pm.type,  # type: ignore[arg-type]
        startDate=pm.start_date, endDate=pm.end_date, timezone=pm.timezone,
        status=compute_status(pm.start_date, pm.end_date),  # type: ignore[arg-type]
        meetingNumber=pm.number, city=pm.city, country=pm.country,
        sources=MeetingSourceFolders(meetingFolder=folder, inbox=f"{folder}Inbox/" if folder else None,
                                     agenda=f"{folder}Agenda/" if folder else None),
        lastIngestedAt=_iso(now), workingGroup="RAN",
    )
    phase = remote_ftp.meeting_phase(pm.start_date, pm.end_date, today)
    urls = []
    for f in candidate_folders(folder, phase):
        try:
            urls += list_folder(f)
        except Exception as exc:  # noqa: BLE001 - a missing Chair folder is normal
            print(f"  {f}: {exc}")
    pat = time_plan_re(pm.number)
    hits = [(unquote(u.rstrip("/").rsplit("/", 1)[-1]), u) for u in urls]
    hits = [(n, u) for n, u in hits if pat.search(n)]
    plan_url = max(hits, key=lambda nu: plan_rank(nu[0]))[1] if hits else None
    print(f"  {meeting.name}: phase {phase}; time plan {plan_url or 'none'}")

    rooms: list[Room] = []
    sessions: list[Session] = []
    sources: list[ScheduleSource] = []
    problems: list[str] = []
    if plan_url and (raw := download_to_temp(plan_url)) and (path := _docx_from(raw, pm.number)):
        src = _source(meeting, plan_url, path, "RAN Plenary time plan", "main_schedule", now)
        rooms, sessions, problems = parse_time_plan(path, meeting, src)
        sources.append(src)
    agenda: list[AgendaItem] = []
    for a_url in ([f"{folder}Agenda/agenda.csv"] if folder else []) + ([SYNC_AGENDA + "agenda.csv"] if phase in ("week", "edge") else []):
        try:
            r = requests.get(a_url, timeout=30)
            if r.ok and r.text.strip():
                agenda = parse_agenda_csv(r.content.decode("utf-8", "replace"), meeting.id)
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
                            message=None if sessions else "No RAN Plenary time plan published yet."),
    )
