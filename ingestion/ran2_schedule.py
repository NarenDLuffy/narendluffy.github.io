"""RAN2 schedule: one week grid per meeting (R2_<n>_Schedule_vNN.docx).

Layout: header row of rooms ("Main room", "Brk 1 room", ...), a weekday row,
then one row per session slot ("09:00 – 10:30") with each room's agenda items
as "[9.3.2] 6GR Control Plane" lines. Rules shared with RAN1 (ingestion/AGENTS.md):

* only active visible Word text counts (struck/deleted items never enter);
* times are never invented — a slot splits only at a time the chair wrote
  ("@9:30", "@9:30-10:30", "From 15:30", "14:30-15:30 …"), otherwise it stays
  one block listing its items;
* vertical-merge continuation cells are never re-read;
* newest revision wins; official beats Draft;
* the date rule (remote_ftp.meeting_phase) picks the folders.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timedelta, timezone

import ingestion.remote_ftp as remote_ftp

from .docx_active_text import active_element_text
from .groups import GROUPS
from .meeting_discovery import compute_status, revision_parts
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

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
#: Problems that must refuse the publish (validator reads COVERAGE_GAPS via live).
PROBLEMS: dict[str, list[str]] = {}

_T = r"(\d{1,2})(?:[:.h]\s?(\d{2}))?"
SLOT_RE = re.compile(rf"^\s*{_T}\s*[–—-]\s*{_T}\s*$")
# A chair-written time at the start of a line: "@9:30", "@ 12:30", "@10-11",
# "From 15:30:", "14:30-15:30 Offline…", "14:30 [9.3.2.5] …".
MARK_RE = re.compile(
    rf"^\s*(?:(?P<at>@)\s*|(?P<from>from)\s+)?(?P<h1>\d{{1,2}})(?:\s?[:.]?\s?(?P<m1>[0-5]\d))?"
    rf"(?:\s*[–—-]\s*(?P<h2>\d{{1,2}})(?:\s?[:.]?\s?(?P<m2>[0-5]\d))?)?\s*:?(?=\s|$|\[)",
    re.I,
)
CODE_RE = re.compile(r"\[\[?\s*(\d+(?:\.\d+)*)\s*(?:\]|(?=\s))")
# "[2]", "[0.5]" after a title are time budgets (TUs), not agenda items.
BUDGET_RE = re.compile(r"^\d(?:\.5)?$")


def _hhmm(h: str, m: str | None) -> str:
    return f"{int(h):02d}:{int(m or 0):02d}"


def _mins(t: str) -> int:
    return int(t[:2]) * 60 + int(t[3:])


def _fmt(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


# --- source discovery ---------------------------------------------------------

def schedule_file_re(number: int, bis: bool) -> re.Pattern[str]:
    suffix = r"(?:-?bis|b)" if bis else r"(?!\d|-?bis|b)"
    return re.compile(rf"(?:^|[^a-z])R2[-_ ]?{number}{suffix}[-_ ].*schedule", re.I)


def agenda_file_re(number: int, bis: bool) -> re.Pattern[str]:
    suffix = r"(?:-?bis|b)" if bis else r"(?!\d|-?bis|b)"
    return re.compile(rf"(?:^|[^a-z])R2[-_ ]?{number}{suffix}[-_ ]agenda", re.I)


def _rank(name: str) -> tuple:
    official = not re.match(r"^\s*draft", name, re.I)
    return (official, revision_parts(name) or [])


def candidate_folders(meeting: Meeting, phase: str) -> list[str]:
    sync = GROUPS["RAN2"].sync_root + "Agenda/"
    own = [meeting.sources.agenda] if meeting.sources and meeting.sources.agenda else []
    archive = ["https://www.3gpp.org/ftp/RAN/RAN2/Agenda/"]
    if phase == "week":
        return [sync]
    if phase == "edge":
        return [sync, *own, *archive]
    return [*own, *archive]


def pick_latest(urls: list[str], pattern: re.Pattern[str]) -> str | None:
    names = [(u.rstrip("/").rsplit("/", 1)[-1], u) for u in urls]
    hits = [(n, u) for n, u in names if pattern.search(n) and n.lower().endswith(".docx")]
    if not hits:
        return None
    return max(hits, key=lambda nu: _rank(nu[0]))[1]


# --- parsing --------------------------------------------------------------------

def _grid_rows(table):
    """Rows of (col, tc, merge) with gridSpan expanded; merge is restart/continue/None."""
    for tr in table._tbl.iter(f"{W}tr"):
        col = 0
        row = []
        for tc in tr.iter(f"{W}tc"):
            pr = tc.find(f"{W}tcPr")
            span, merge = 1, None
            if pr is not None:
                gs = pr.find(f"{W}gridSpan")
                if gs is not None:
                    span = int(gs.get(f"{W}val") or 1)
                vm = pr.find(f"{W}vMerge")
                if vm is not None:
                    merge = vm.get(f"{W}val") or "continue"
            row.append((col, tc, merge))
            col += span
        yield row


def _codes(line: str) -> list[str]:
    out: list[str] = []
    for m in CODE_RE.finditer(line):
        code = m.group(1)
        before = line[: m.start()].strip()
        # A small bracket number after text is a time budget: "NR20 AIoT [2]".
        # "[AT136][004]" e-mail discussion numbers are not agenda items.
        if "." not in code and (code.startswith("0") or int(code) >= 30):
            continue
        if BUDGET_RE.match(code) and before and not before.endswith((",", "-", "]")) and not CODE_RE.search(before[-12:]):
            continue
        if code not in out:
            out.append(code)
    return out


def _clean_label(line: str) -> str:
    text = CODE_RE.sub("", line)
    # Letter-only tags name the topic ("[MOB] offlines" -> "MOB offlines");
    # tags with digits are budgets or e-mail numbers ([2], [AT136][004]).
    text = re.sub(r"\[([A-Za-z][A-Za-z/&\- ]*)\]", r"\1", text)
    text = re.sub(r"\[[^\]]*\]", "", text)
    return re.sub(r"\s+", " ", text).strip(" :,-–")


def split_cell(text: str, start: str, end: str) -> list[dict]:
    """Segments of one cell; splits only at chair-written times."""
    s0, e0 = _mins(start), _mins(end)
    segs: list[dict] = []
    current = {"start": s0, "end": None, "lines": []}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = MARK_RE.match(line)
        if m and (m.group("at") or m.group("from") or m.group("m1") or m.group("h2")):
            t1 = _mins(_hhmm(m.group("h1"), m.group("m1")))
            t2 = _mins(_hhmm(m.group("h2"), m.group("m2"))) if m.group("h2") else None
            # Only times that sit in (or touch) this slot are a split.
            if s0 - 60 <= t1 < e0 and (t2 is None or t2 > t1):
                rest = line[m.end():].strip(" :")
                if current["lines"] and t1 <= current["start"] and not segs:
                    # "@8:30" at the slot start under a heading: same segment.
                    if rest:
                        current["lines"].append(rest)
                    current["end"] = t2
                    continue
                if current["lines"]:
                    segs.append(current)
                current = {"start": t1, "end": t2, "lines": [rest] if rest else []}
                continue
        current["lines"].append(line)
    if current["lines"]:
        segs.append(current)
    if not segs:
        return []
    # Starts must increase; otherwise the chair's times don't form a timeline.
    starts = [s["start"] for s in segs]
    if any(b <= a for a, b in zip(starts, starts[1:])):
        return [{"start": s0, "end": e0, "lines": [l for s in segs for l in s["lines"]]}]
    for i, seg in enumerate(segs):
        nxt = segs[i + 1]["start"] if i + 1 < len(segs) else e0
        if seg["end"] is None:
            seg["end"] = max(nxt, seg["start"] + 1) if i + 1 < len(segs) else max(e0, seg["start"] + 1)
        else:
            seg["end"] = min(seg["end"], nxt) if i + 1 < len(segs) else seg["end"]
    return [s for s in segs if s["end"] > s["start"]]


def _breaks(paragraphs: list[str]) -> list[tuple[str, str, str]]:
    out = []
    for p in paragraphs:
        m = re.match(rf"^\s*(.*?(coffee|lunch|break).*?):?\s+{_T}\s*(?:to|[–—-])\s*{_T}", p, re.I)
        if m:
            kind = "lunch" if "lunch" in m.group(1).lower() else "break"
            out.append((kind, _hhmm(m.group(3), m.group(4)), _hhmm(m.group(5), m.group(6))))
    return out


def _day_date(meeting: Meeting, weekday: int) -> str:
    start = date.fromisoformat(meeting.startDate)
    return (start + timedelta(days=(weekday - start.weekday()) % 7)).isoformat()


def _key(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:10]


def parse_ran2_docx(path: str, meeting: Meeting, source: ScheduleSource):
    import docx  # python-docx

    doc = docx.Document(path)
    paragraphs = [active_element_text(p._p) for p in doc.paragraphs]
    rooms: dict[int, Room] = {}
    sessions: list[Session] = []
    problems: list[str] = []
    for ti, table in enumerate(doc.tables):
        day: str | None = None
        open_cells: dict[int, list[Session]] = {}
        for ri, row in enumerate(_grid_rows(table)):
            texts = [(c, tc, mg, active_element_text(tc)) for c, tc, mg in row]
            if not texts:
                continue
            first = texts[0][3].strip()
            if ri == 0 or (not rooms and any("room" in t[3].lower() for t in texts[1:])):
                for c, _tc, _mg, t in texts[1:]:
                    name = re.sub(r"\*+$", "", t.strip()).strip()
                    if name:
                        rid = f"{meeting.id}-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}"
                        label = "RAN2 Main" if "main" in name.lower() else "RAN2 " + re.sub(r"(?i)\s*room\b", "", name).replace("Brk ", "Brk").strip()
                        rooms[c] = Room(roomId=rid, meetingId=meeting.id, roomName=name, order=len(rooms),
                                        sessionLabel=label,
                                        chairRole="main" if "main" in name.lower() else None)
                continue
            wd = next((i for i, d in enumerate(WEEKDAYS) if first.lower().startswith(d)), None)
            if wd is not None:
                day = _day_date(meeting, wd)
                open_cells = {}
                continue
            slot = SLOT_RE.match(first)
            if not slot or day is None:
                continue  # social rows ("Colorful Polo Day")
            start, end = _hhmm(slot.group(1), slot.group(2)), _hhmm(slot.group(3), slot.group(4))
            if _mins(end) <= _mins(start):
                continue
            for c, _tc, merge, text in texts[1:]:
                room = rooms.get(c)
                if room is None:
                    continue
                if merge == "continue":
                    # Never re-read; a longer merged row only stretches the block.
                    for s in open_cells.get(c, []):
                        if s.endTime == open_cells[c][-1].endTime and _mins(end) > _mins(s.endTime):
                            s.endTime = end
                    continue
                if not text.strip():
                    open_cells[c] = []
                    continue
                emitted = []
                for seg in split_cell(text, start, end):
                    lines = seg["lines"]
                    codes = [code for l in lines for code in _codes(l)]
                    codes = list(dict.fromkeys(codes))
                    labels = [_clean_label(l) for l in lines]
                    topic = next((l for l in labels if l), codes[0] if codes else "Session")
                    if topic.startswith("(") and lines:
                        # "[AT136][102][MOB] (Ericsson)": keep the discussion tag.
                        topic = re.sub(r"\s+", " ", lines[0]).strip()
                    slots = []
                    for l in lines:
                        for code in _codes(l):
                            slots.append(AgendaSlot(code=code, label=_clean_label(l) or code))
                    cell = f"{source.fileName}|{ti}|{day}|{start}-{end}|{c}|{_key(text)}"
                    sid = f"{meeting.id}-{_key(day, room.roomId, _fmt(seg['start']), topic)}"
                    note = None
                    if seg["start"] < _mins(start) or seg["end"] > _mins(end):
                        note = f"Chair-written time {_fmt(seg['start'])}–{_fmt(seg['end'])} is outside the {start}–{end} slot."
                    lead = re.search(r"\(([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)?)\)", " ".join(lines))
                    s = Session(
                        sessionId=sid, meetingId=meeting.id, date=day,
                        day=WEEKDAYS[date.fromisoformat(day).weekday()].capitalize(),
                        startTime=_fmt(seg["start"]), endTime=_fmt(seg["end"]),
                        roomId=room.roomId, roomName=room.roomName,
                        topic=topic[:160], topicKey=_key(topic.lower())[:8],
                        agendaItems=codes, agendaBreakdown=slots,
                        sessionLead=lead.group(1) if lead else None,
                        mode="offline" if re.search(r"\boffline", " ".join(lines), re.I) else None,
                        note=note,
                        sources=[SessionSourceRef(sourceId=source.sourceId, contributed=codes, cell=cell)],
                        derivation="ran2-grid",
                    )
                    sessions.append(s)
                    emitted.append(s)
                if not emitted:
                    problems.append(f"{day} {room.roomName} {start}-{end}: cell has text but no block was published")
                open_cells[c] = emitted
    # One room never holds two blocks at once. A chair-written later start
    # ("@10:00" after an open-ended item) shortens the earlier item; any other
    # overlap is a reading problem and refuses the publish.
    by_room: dict[tuple, list[Session]] = {}
    for s in sessions:
        by_room.setdefault((s.date, s.roomId), []).append(s)
    kept: list[Session] = []
    for group in by_room.values():
        group.sort(key=lambda x: x.startTime)
        last_end = ""
        for s in group:
            if last_end and s.startTime < last_end:
                problems.append(
                    f"{s.date} {s.roomName} {s.startTime}-{s.endTime} {s.topic}: overlaps the previous item (ends {last_end})"
                )
            kept.append(s)
            last_end = max(last_end, s.endTime)
    # Breaks from the "Breaks" paragraph, in every room and day without a session then.
    days = sorted({s.date for s in kept})
    for kind, bs, be in _breaks(paragraphs):
        for d in days:
            for room in rooms.values():
                clash = any(s.date == d and s.roomId == room.roomId and s.startTime < be and s.endTime > bs for s in kept)
                if clash or not any(s.date == d and s.roomId == room.roomId for s in kept):
                    continue
                kept.append(Session(
                    sessionId=f"{meeting.id}-{_key(d, room.roomId, bs, kind)}", meetingId=meeting.id, date=d,
                    day=WEEKDAYS[date.fromisoformat(d).weekday()].capitalize(), startTime=bs, endTime=be,
                    roomId=room.roomId, roomName=room.roomName,
                    topic="Lunch" if kind == "lunch" else "Coffee break", topicKey=kind, kind=kind,
                ))
    kept.sort(key=lambda s: (s.date, s.startTime, s.roomId))
    return list(rooms.values()), kept, problems


def parse_agenda_docx(path: str, meeting_id: str) -> list[AgendaItem]:
    import docx

    doc = docx.Document(path)
    lines = [active_element_text(p._p) for p in doc.paragraphs]
    for t in doc.tables:
        for r in t.rows:
            lines.extend(active_element_text(c._tc) for c in r.cells)
    items: dict[str, AgendaItem] = {}
    for line in lines:
        for l in line.splitlines():
            m = re.match(r"^\s*(\d+(?:\.\d+)*)\.?\s+(\S.*)$", l)
            if m and len(m.group(2)) < 200 and m.group(1) not in items:
                code = m.group(1)
                items[code] = AgendaItem(code=code, meetingId=meeting_id, title=m.group(2).strip(),
                                         parent=code.rsplit(".", 1)[0] if "." in code else None,
                                         topicKey=_key(m.group(2).lower())[:8])
    return list(items.values())


# --- bundle -------------------------------------------------------------------

def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_bundle(pm: PortalMeeting, *, today: date | None = None) -> ScheduleBundle:
    from .live import download_to_temp

    now = datetime.now(timezone.utc)
    folder = pm.folder_url
    meeting = Meeting(
        id=pm.slug, slug=pm.slug, name=pm.name, type=pm.type,  # type: ignore[arg-type]
        startDate=pm.start_date, endDate=pm.end_date, timezone=pm.timezone,
        status=compute_status(pm.start_date, pm.end_date),  # type: ignore[arg-type]
        meetingNumber=pm.number, city=pm.city, country=pm.country,
        sources=MeetingSourceFolders(
            meetingFolder=folder,
            inbox=f"{folder}Inbox/" if folder else None,
            agenda=f"{folder}Agenda/" if folder else None,
        ),
        lastIngestedAt=_iso(now), workingGroup="RAN2",
    )
    phase = remote_ftp.meeting_phase(pm.start_date, pm.end_date, today)
    urls: list[str] = []
    for f in candidate_folders(meeting, phase):
        urls.extend(list_folder(f))
    bis = pm.type == "bis"
    sched_url = pick_latest(urls, schedule_file_re(pm.number, bis))
    agenda_url = pick_latest(urls, agenda_file_re(pm.number, bis))
    print(f"  {pm.name}: phase {phase}, {len(urls)} file(s); schedule {sched_url or 'none'}")

    rooms: list[Room] = []
    sessions: list[Session] = []
    sources: list[ScheduleSource] = []
    agenda: list[AgendaItem] = []
    PROBLEMS[meeting.id] = []
    if agenda_url:
        path = download_to_temp(agenda_url)
        if path:
            try:
                agenda = parse_agenda_docx(path, meeting.id)
            except Exception as exc:
                print(f"  agenda unreadable: {exc}")
    if sched_url:
        path = download_to_temp(sched_url)
        name = sched_url.rsplit("/", 1)[-1]
        if path:
            data = open(path, "rb").read()
            source = ScheduleSource(
                sourceId=f"{meeting.id}-{_key(name)}", meetingId=meeting.id, fileName=name,
                label="RAN2 session schedule", type="main_schedule",
                origin="public", retrievedAt=_iso(now),
                revision=(re.search(r"v\d+", name, re.I) or [None])[0],
                revisionParts=revision_parts(name), url=sched_url,
                contentHash=hashlib.sha256(data).hexdigest(),
            )
            rooms, sessions, problems = parse_ran2_docx(path, meeting, source)
            PROBLEMS[meeting.id] = problems
            sources = [source]
    # Titles the schedule itself gives ("[7.6] NR17/18/19 Mob") fill agenda gaps.
    known = {a.code for a in agenda}
    for s in sessions:
        for slot in s.agendaBreakdown:
            if slot.code and slot.code not in known and slot.label and slot.label != slot.code:
                agenda.append(AgendaItem(code=slot.code, meetingId=meeting.id, title=slot.label,
                                         parent=slot.code.rsplit(".", 1)[0] if "." in slot.code else None))
                known.add(slot.code)
    # Name-only blocks ("ISAC offline (Xiaomi)") get their agenda item from
    # the RAN2 agenda titles; unclear ones stay unlinked and are reported.
    from .ran2_topics import resolve_topic
    titles = {a.code: a.title for a in agenda}
    for s in sessions:
        if s.agendaItems or s.kind in ("break", "lunch"):
            continue
        code = resolve_topic(s.topic, titles)
        if code:
            s.agendaItems = [code]
    meeting.schedulePublished = bool(sessions)
    return ScheduleBundle(
        generatedAt=_iso(now), meeting=meeting, rooms=rooms, sessions=sessions,
        agendaItems=agenda, sources=sources,
        ingest=IngestStatus(state="ok", lastSuccessfulAt=_iso(now), lastAttemptAt=_iso(now),
                            message=None if sessions else "No RAN2 session schedule published yet."),
    )
