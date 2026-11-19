"""RAN3 schedule: main session from the chair notes, offlines from a spreadsheet.

* Main (online) session: the weekday table ("Monday | Tuesday | ...") at the
  end of the newest Chairs_Notes DOCX (RAN3_<n>_agenda_YYYYMMDD_HHMM[_L].docx).
  Row times come only from the first column; a row without a written time is
  bounded by the rows above and below (the breaks). Unbounded rows are problems.
  Lines naming an offline ("6G Offline (CB#5)") go to the parallel 6G offline lane.
* Offline rooms: RAN3 offline discussion_ver_NN.xlsx, one sheet per day
  ("Nov16 Mon"), 30-minute rows Time Slot | Topic | Moderator. The room is the
  trailing tag ("ISAC offline (GTW)"); equal consecutive rows merge.
Shared rules (ingestion/AGENTS.md): active Word text only, newest revision wins,
the date rule (remote_ftp.meeting_phase) picks the folders, overlaps refuse the publish.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timezone

import ingestion.remote_ftp as remote_ftp

from .docx_active_text import active_element_text
from .groups import GROUPS
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
from .ran2_schedule import PROBLEMS, WEEKDAYS, _day_date, _grid_rows, _iso, _key

TIME_RE = re.compile(r"(?<!\d)(\d{1,2})[:.]?(\d{2})(?!\d)")
_AI_ONE = r"\d+(?:\.\d+)*(?:\s*/\s*[A-Z](?![a-z]))?(?:\s*-\s*\d+)?"
AI_RE = re.compile(rf"\bAI\s*:?\s*({_AI_ONE}(?:\s*,\s*{_AI_ONE})*)", re.I)
BREAK_RE = re.compile(r"^\s*(coffee|lunch)\s*break\b", re.I)
SKIP_RE = re.compile(r"start of meeting|^no (parallel )?offlines?\b|offline in main room", re.I)
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _fmt(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


# --- source discovery ---------------------------------------------------------

def chair_notes_re(number: int, bis: bool) -> re.Pattern[str]:
    suffix = r"(?:-?bis|b)" if bis else r"(?!\d|-?bis|b)"
    return re.compile(rf"R(?:AN)?3[-_ ]?{number}{suffix}[-_ ].*agenda.*\.docx$", re.I)


OFFLINE_RE = re.compile(r"offline.*\.xlsx$", re.I)


def notes_rank(name: str) -> tuple:
    m = re.search(r"(\d{8})[_-](\d{4})", name)
    return (m.group(1) + m.group(2) if m else "", "_l" in name.lower(), name)


def offline_rank(name: str) -> tuple:
    m = re.search(r"ver[_ ]?(\d+)", name, re.I)
    return (int(m.group(1)) if m else -1, name)


def candidate_folders(meeting_folder: str | None, phase: str) -> tuple[list[str], list[str]]:
    """(chair-notes folders, offline-sheet folders) for the date rule."""
    sync = GROUPS["RAN3"].sync_root
    own = meeting_folder or ""
    notes_sync, off_sync = [sync + "Inbox/Chairs_Notes/"], [sync + "Offline_meeting_room/"]
    notes_own = [own + "Inbox/Chairs_Notes/"] if own else []
    off_own = [own + "Offline_meeting_room/"] if own else []
    archive_n, archive_o = ["https://www.3gpp.org/ftp/RAN/RAN3/Inbox/Chairs_Notes/"], ["https://www.3gpp.org/ftp/RAN/RAN3/Offline_meeting_room/"]
    if phase == "week":
        return notes_sync, off_sync
    if phase == "edge":
        return notes_sync + notes_own + archive_n, off_sync + off_own + archive_o
    return notes_own + archive_n, off_own


def pick(urls: list[str], ok, rank) -> str | None:
    hits = [(u.rstrip("/").rsplit("/", 1)[-1], u) for u in urls]
    hits = [(n, u) for n, u in hits if ok(n) and not n.startswith("~$")]
    return max(hits, key=lambda nu: rank(nu[0]))[1] if hits else None


# --- agenda codes -------------------------------------------------------------

def ai_codes(text: str) -> list[str]:
    """ "6G SI: AI 10.1, 10.3.2" -> [10.1, 10.3.2]; "AI 1-8" -> 1..8; "AI 12/L" -> 12; "[AI:11.2]" -> 11.2."""
    out: list[str] = []
    for m in AI_RE.finditer(text):
        for part in re.split(r"\s*,\s*", m.group(1).strip(" ,")):
            part = re.sub(r"\s*/\s*[A-Z]$", "", part.strip(), flags=re.I)
            rng = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
            if rng and int(rng.group(1)) < int(rng.group(2)) <= 40:
                out.extend(str(i) for i in range(int(rng.group(1)), int(rng.group(2)) + 1))
            elif re.fullmatch(r"\d+(?:\.\d+)*", part):
                out.append(part)
    return list(dict.fromkeys(out))


def _words(text: str) -> set[str]:
    stop = {"offline", "offlines", "the", "and", "for", "phase", "led"}
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in stop and not re.fullmatch(r"r(?:el)?\d+", w)}


def _title_terms(title: str) -> set[str]:
    words = re.findall(r"[A-Za-z0-9]+", title)
    terms = _words(title)
    for n in range(2, 6):  # acronyms: "Integrated Sensing And Communication" -> isac
        for i in range(len(words) - n + 1):
            terms.add("".join(w[0] for w in words[i:i + n]).lower())
    return terms


def resolve_topic(topic: str, titles: dict[str, str]) -> str | None:
    """Agenda code whose title holds every significant topic word (or its acronym); unique match only."""
    tw = _words(topic)
    if not tw:
        return None
    hits = [c for c, t in titles.items() if tw <= _title_terms(t)]
    hits = [c for c in hits if not any(c.startswith(o + ".") for o in hits)]
    return hits[0] if len(hits) == 1 else None


# --- parsing --------------------------------------------------------------------

def _room(meeting: Meeting, name: str, label: str, order: int, main: bool = False) -> Room:
    rid = f"{meeting.id}-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}"
    return Room(roomId=rid, meetingId=meeting.id, roomName=name, order=order,
                sessionLabel=label, chairRole="main" if main else None)


def _session(meeting, room, day, s, e, lines, source, cell, mode=None, kind="session", lead=None) -> Session:
    text = "; ".join(lines)
    codes = ai_codes(text)
    topic = re.sub(r"\s+", " ", lines[0]).strip(" *") if lines else "Session"
    note = " · ".join(l.strip(" *") for l in lines[1:]) or None
    return Session(
        sessionId=f"{meeting.id}-{_key(day, room.roomId, _fmt(s), topic)}", meetingId=meeting.id,
        date=day, day=WEEKDAYS[date.fromisoformat(day).weekday()].capitalize(),
        startTime=_fmt(s), endTime=_fmt(e), roomId=room.roomId, roomName=room.roomName,
        topic=topic[:160], topicKey=_key(topic.lower())[:8], agendaItems=codes,
        agendaBreakdown=[AgendaSlot(code=c, label=topic) for c in codes],
        sessionLead=lead, mode=mode, note=note, kind=kind,  # type: ignore[arg-type]
        sources=[] if kind != "session" else [SessionSourceRef(sourceId=source.sourceId, contributed=codes, cell=cell)],
        derivation="ran3-grid",
    )


def parse_chair_grid(path: str, meeting: Meeting, source: ScheduleSource):
    """Main + 6G offline lane from the weekday table at the end of the chair notes."""
    import docx

    doc = docx.Document(path)
    table = next((t for t in reversed(doc.tables)
                  if sum(d in active_element_text(t._tbl).lower() for d in WEEKDAYS[:5]) >= 2), None)
    problems: list[str] = []
    if table is None:
        return [], [], ["chair notes: no Monday–Friday table found"]
    rows = [[(c, tc, mg, active_element_text(tc)) for c, tc, mg in r] for r in _grid_rows(table)]
    header = rows[0]
    days: dict[int, str] = {}
    for c, _tc, _mg, t in header:
        wd = next((i for i, d in enumerate(WEEKDAYS) if t.strip().lower().startswith(d)), None)
        if wd is not None:
            days[c] = _day_date(meeting, wd)
    # Group rows by a vertically merged time cell; each group is one time span.
    groups: list[dict] = []
    for r in rows[1:]:
        first = r[0]
        if first[2] == "continue" and groups:
            groups[-1]["rows"].append(r)
            continue
        times = [int(h) * 60 + int(m) for h, m in TIME_RE.findall(first[3])]
        groups.append({"times": times, "rows": [r]})
    # A merged time cell listing one time per row ("08:00 / 08:30" over two rows)
    # gives each row its start; the group's end is the next group's start.
    split: list[dict] = []
    for g in groups:
        if len(g["rows"]) > 1 and len(g["times"]) == len(g["rows"]):
            split.extend({"times": [t], "rows": [r]} for t, r in zip(g["times"], g["rows"]))
        else:
            split.append(g)
    groups = split
    for i, g in enumerate(groups):
        g["start"] = g["times"][0] if g["times"] else None
        g["end"] = g["times"][1] if len(g["times"]) > 1 else None
    for i, g in enumerate(groups):
        if g["end"] is None and i + 1 < len(groups):
            g["end"] = groups[i + 1]["start"]
        if g["start"] is None and i > 0:
            g["start"] = groups[i - 1]["end"]
    main = _room(meeting, "Main", "RAN3 Main", 0, main=True)
    lane = _room(meeting, "6G offline", "RAN3 6G offline", 1)
    sessions: list[Session] = []
    last: dict[int, list[Session]] = {}
    for gi, g in enumerate(groups):
        for c, day in days.items():
            first_cell = next((x for x in g["rows"][0] if x[0] == c), None)
            if first_cell is not None and first_cell[2] == "continue":
                # Never re-read a merge continuation; it only stretches the block.
                for prev in last.get(c, []):
                    if g["end"] is not None:
                        prev.endTime = _fmt(max(g["end"], int(prev.endTime[:2]) * 60 + int(prev.endTime[3:])))
                continue
            before = len(sessions)
            main_lines: list[str] = []
            off_lines: list[str] = []
            for r in g["rows"]:
                cell = next((x for x in r if x[0] == c), None)
                if cell is None or cell[2] == "continue":
                    continue
                for line in (l.strip() for l in cell[3].splitlines()):
                    if not line or SKIP_RE.search(line):
                        continue
                    target = off_lines if re.search(r"\boffline", line, re.I) else main_lines
                    if line not in target:
                        target.append(line)
            if not main_lines and not off_lines:
                last[c] = []
                continue
            s, e = g["start"], g["end"]
            if s is None or e is None or e <= s:
                problems.append(f"{day} RAN3 main grid row {gi + 1}: '{(main_lines + off_lines)[0]}' has no readable start/end time")
                continue
            cell_id = f"{source.fileName}|grid|{day}|{_fmt(s)}-{_fmt(e)}|{c}"
            brk = [l for l in main_lines if BREAK_RE.match(l)]
            if brk:
                kind = "lunch" if "lunch" in brk[0].lower() else "break"
                sessions.append(_session(meeting, main, day, s, e, ["Lunch" if kind == "lunch" else "Coffee break"],
                                         source, cell_id, kind=kind))
                main_lines = [l for l in main_lines if l not in brk]
            if main_lines:
                sessions.append(_session(meeting, main, day, s, e, main_lines, source, cell_id + "|main", mode="online"))
            if off_lines:
                sessions.append(_session(meeting, lane, day, s, e, off_lines, source, cell_id + "|off", mode="offline"))
            last[c] = sessions[before:]
    return [main, lane], merge_runs(sessions), problems


def merge_runs(sessions: list[Session]) -> list[Session]:
    """Back-to-back blocks with the same text in one room become one block."""
    out: list[Session] = []
    for s in sorted(sessions, key=lambda x: (x.date, x.roomId, x.startTime)):
        p = out[-1] if out else None
        if p and p.date == s.date and p.roomId == s.roomId and p.endTime == s.startTime \
                and (p.topic, p.note, p.kind) == (s.topic, s.note, s.kind):
            p.endTime = s.endTime
            continue
        out.append(s)
    return out


def _sheet_date(title: str, meeting: Meeting) -> str | None:
    m = re.search(r"([A-Za-z]{3})[a-z]*\s*(\d{1,2})", title)
    if not m or m.group(1).lower() not in MONTHS:
        return None
    start = date.fromisoformat(meeting.startDate)
    d = date(start.year, MONTHS[m.group(1).lower()], int(m.group(2)))
    if d < start.replace(day=1) and d.month < start.month:
        d = d.replace(year=start.year + 1)
    return d.isoformat()


def parse_offline_sheet(path: str, meeting: Meeting, source: ScheduleSource, order0: int = 2):
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True)
    rooms: dict[str, Room] = {}
    sessions: list[Session] = []
    problems: list[str] = []
    for ws in wb.worksheets:
        day = _sheet_date(ws.title, meeting)
        if not day:
            continue
        open_: dict | None = None
        runs: list[dict] = []
        for ri, row in enumerate(ws.iter_rows(values_only=True), 1):
            slot = str(row[0] or "")
            tm = TIME_RE.findall(slot)
            if len(tm) < 2:
                continue
            s, e = (int(h) * 60 + int(m) for h, m in tm[:2])
            topic = re.sub(r"\s+", " ", str(row[1] or "")).strip() if len(row) > 1 else ""
            mod = re.sub(r"\s*\n\s*", ", ", str(row[2] or "")).strip() if len(row) > 2 else ""
            if not topic or SKIP_RE.search(topic):
                open_ = None
                continue
            if open_ and open_["topic"] == topic and open_["mod"] == mod and open_["end"] == s:
                open_["end"] = e
                continue
            open_ = {"topic": topic, "mod": mod, "start": s, "end": e, "row": ri}
            runs.append(open_)
        for r in runs:
            tag = re.search(r"\(([A-Z][A-Za-z0-9 ]{1,15})\)\s*$", r["topic"])
            name = tag.group(1).strip() if tag else "Offline"
            topic = r["topic"][: tag.start()].strip() if tag else r["topic"]
            topic = re.sub(r"\[\s*AI\s*:[^\]]*\]", "", topic).strip() or r["topic"]
            if name not in rooms:
                rooms[name] = _room(meeting, f"Offline {name}" if name != "Offline" else "Offline",
                                    f"RAN3 offline {name}" if name != "Offline" else "RAN3 offline", order0 + len(rooms))
            room = rooms[name]
            ses = _session(meeting, room, day, r["start"], r["end"], [topic], source,
                           f"{source.fileName}|{ws.title}|{day}|row{r['row']}", mode="offline", lead=r["mod"] or None)
            codes = ai_codes(r["topic"])
            ses.agendaItems = codes
            ses.agendaBreakdown = [AgendaSlot(code=c, label=topic) for c in codes]
            ses.sources[0].contributed = codes
            sessions.append(ses)
    return list(rooms.values()), sessions, problems


def parse_agenda(path: str, meeting_id: str) -> list[AgendaItem]:
    import docx

    doc = docx.Document(path)
    lines = [active_element_text(p._p) for p in doc.paragraphs]
    for t in doc.tables:
        for r in t.rows:
            lines.extend(active_element_text(c._tc) for c in r.cells)
    items: dict[str, AgendaItem] = {}
    for line in lines:
        for l in line.splitlines():
            m = re.match(r"^\s*([1-9]\d?(?:\.\d+)*)\.?\s+([A-Za-z].*)$", l)
            if not m or len(m.group(2)) > 200 or m.group(1) in items:
                continue
            code = m.group(1)
            if "." not in code and int(code) > 40:
                continue
            items[code] = AgendaItem(code=code, meetingId=meeting_id, title=m.group(2).strip(),
                                     parent=code.rsplit(".", 1)[0] if "." in code else None,
                                     topicKey=_key(m.group(2).lower())[:8])
    return list(items.values())


def overlap_problems(sessions: list[Session]) -> list[str]:
    out = []
    by: dict[tuple, list[Session]] = {}
    for s in sessions:
        by.setdefault((s.date, s.roomId), []).append(s)
    for group in by.values():
        group.sort(key=lambda x: x.startTime)
        last = ""
        for s in group:
            if last and s.startTime < last:
                out.append(f"{s.date} {s.roomName} {s.startTime}-{s.endTime} {s.topic}: overlaps the previous item (ends {last})")
            last = max(last, s.endTime)
    return out


# --- bundle -------------------------------------------------------------------

def _source(meeting: Meeting, url: str, path: str, label: str, kind: str, now: datetime) -> ScheduleSource:
    from urllib.parse import unquote

    name = unquote(url.rsplit("/", 1)[-1])
    data = open(path, "rb").read()
    rev = re.search(r"\d{8}[_-]\d{4}(?:_L)?|ver[_ ]?\d+", name, re.I)
    return ScheduleSource(
        sourceId=f"{meeting.id}-{_key(name)}", meetingId=meeting.id, fileName=name, label=label,
        type=kind, origin="public", retrievedAt=_iso(now), revision=rev.group(0) if rev else None,  # type: ignore[arg-type]
        revisionParts=[int(x) for x in re.findall(r"\d+", rev.group(0))] if rev else [], url=url,
        contentHash=hashlib.sha256(data).hexdigest(),
    )


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
        sources=MeetingSourceFolders(meetingFolder=folder, inbox=f"{folder}Inbox/" if folder else None,
                                     agenda=f"{folder}Agenda/" if folder else None),
        lastIngestedAt=_iso(now), workingGroup="RAN3",
    )
    phase = remote_ftp.meeting_phase(pm.start_date, pm.end_date, today)
    nf, of = candidate_folders(folder, phase)
    note_urls = [u for f in nf for u in list_folder(f)]
    off_urls = [u for f in of for u in list_folder(f)]
    pat = chair_notes_re(pm.number, pm.type == "bis")
    notes_url = pick(note_urls, lambda n: bool(pat.search(unquote(n))), notes_rank)
    # The sheet carries no meeting number: the Sync copy counts only while it
    # holds this meeting (week / day after); otherwise only the meeting's own folder.
    off_url = pick(off_urls, lambda n: bool(OFFLINE_RE.search(unquote(n))), offline_rank)
    print(f"  {pm.name}: phase {phase}; chair notes {notes_url or 'none'}; offline {off_url or 'none'}")

    rooms: list[Room] = []
    sessions: list[Session] = []
    sources: list[ScheduleSource] = []
    agenda: list[AgendaItem] = []
    problems: list[str] = []
    if notes_url and (path := download_to_temp(notes_url)):
        src = _source(meeting, notes_url, path, "RAN3 chair notes (main session)", "main_schedule", now)
        try:
            agenda = parse_agenda(path, meeting.id)
        except Exception as exc:  # noqa: BLE001
            print(f"  agenda unreadable: {exc}")
        r, s, p = parse_chair_grid(path, meeting, src)
        rooms += r; sessions += s; problems += p; sources.append(src)
    if off_url and (path := download_to_temp(off_url)):
        src = _source(meeting, off_url, path, "RAN3 offline discussion rooms", "offline_schedule", now)
        r, s, p = parse_offline_sheet(path, meeting, src, order0=len(rooms))
        rooms += r; sessions += s; problems += p; sources.append(src)
    titles = {a.code: a.title for a in agenda}
    for s in sessions:
        if not s.agendaItems and s.kind == "session":
            code = resolve_topic(s.topic, titles)
            if code:
                s.agendaItems = [code]
    # Drop rooms with no sessions (e.g. an empty 6G offline lane).
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
                            message=None if sessions else "No RAN3 session schedule published yet."),
    )
