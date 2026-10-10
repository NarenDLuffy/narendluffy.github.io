"""One canonical room per cell colour across ALL schedule files of a meeting.

Every colour in the online and offline week-grid tables is one room, whichever
file it comes from. Online vs offline comes from the table heading. Room names
come from any file: the coloured legend above a table, or a one-room table's
heading ("@Yeongju A (1F)", "(room: RAN1_Brk#2, Yeongju B, 1F)"). A name on its
own never creates a column when it matches a coloured room. Nothing here knows
a chair's name or a fixed number of rooms.
"""

from __future__ import annotations

from .block_schedule import norm_room
from .models import Room, Session


def resolve_rooms(
    meeting_id: str, rooms: list[Room], sessions: list[Session]
) -> tuple[list[Room], list[Session]]:
    remap: dict[str, str] = {}
    by_key: dict[str, Room] = {}
    seen_order: dict[str, int] = {}

    def absorb(keeper: Room, other: Room) -> None:
        if other.chairRole == "main":
            keeper.chairRole = "main"
        name = other.roomName or ""
        if name and name != "RAN1 Main" and (
            not keeper.roomName or keeper.roomName == "RAN1 Main" or len(name) > len(keeper.roomName)
        ):
            keeper.roomName = name
            keeper.shortName = name[:24]
        keeper.sessionLabel = keeper.sessionLabel or other.sessionLabel
        keeper.sourceColor = keeper.sourceColor or other.sourceColor

    for index, room in enumerate(rooms):
        key = room.chairLaneId or f"{meeting_id}:name:{norm_room(room.roomName)}"
        keeper = by_key.get(key)
        if keeper is None:
            by_key[key] = room
            remap[room.roomId] = room.roomId
            seen_order[room.roomId] = index
        else:
            remap[room.roomId] = keeper.roomId
            absorb(keeper, room)

    def is_colour(room: Room) -> bool:
        key = room.chairLaneId or ""
        return key.startswith(f"{meeting_id}:online:") or key.startswith(f"{meeting_id}:offline:")

    keepers = list(by_key.values())
    colour_rooms = [r for r in keepers if is_colour(r)]
    for room in list(keepers):
        if is_colour(room):
            continue
        if (room.chairLaneId or "").endswith(":main"):
            target = next((c for c in colour_rooms if c.chairRole == "main"), None)
        else:
            wanted = norm_room(room.roomName)
            target = next(
                (c for c in colour_rooms if c.roomName and norm_room(c.roomName) == wanted), None
            )
        if target is None:
            continue
        absorb(target, room)
        keepers.remove(room)
        for source_id, target_id in list(remap.items()):
            if target_id == room.roomId:
                remap[source_id] = target.roomId

    # Same room, different name: a name-only room whose sessions agree with one
    # coloured room's sessions (same date, overlapping time, same or parent/child
    # agenda) in most slots is that room.
    def current(session: Session) -> str:
        return remap.get(session.roomId, session.roomId)

    colour_ids = {c.roomId for c in colour_rooms if c in keepers}
    for room in list(keepers):
        if is_colour(room):
            continue
        target = _schedule_twin(room, [c for c in keepers if c.roomId in colour_ids], sessions, current)
        if target is None:
            continue
        absorb(target, room)
        keepers.remove(room)
        for source_id, target_id in list(remap.items()):
            if target_id == room.roomId:
                remap[source_id] = target.roomId
        remap[room.roomId] = target.roomId

    used = {remap.get(s.roomId, s.roomId) for s in sessions if s.roomId}
    keepers = [r for r in keepers if r.roomId in used]

    def kind(room: Room) -> int:
        key = room.chairLaneId or ""
        if room.chairRole == "main":
            return 0
        if ":online:" in key:
            return 1
        if ":offline:" in key:
            return 2
        return 3

    keepers.sort(key=lambda r: (kind(r), seen_order.get(r.roomId, 0)))
    counters = {1: 0, 2: 0, 3: 0}
    for index, room in enumerate(keepers):
        group = kind(room)
        if group in counters:
            counters[group] += 1
        if room.chairRole == "main":
            if room.roomName and room.roomName != "RAN1 Main":
                room.sessionLabel = "RAN1 Main"
            else:
                room.roomName, room.sessionLabel = "RAN1 Main", None
        elif not room.roomName:
            room.roomName = f"{'Offline' if group == 2 else 'Online'} room {counters.get(group, 1)}"
        room.shortName = room.roomName[:24]
        room.chairRole = room.chairRole or ("vice" if group in (1, 2) else None)
        room.order = index

    names = {room.roomId: room.roomName for room in keepers}
    for session in sessions:
        session.roomId = remap.get(session.roomId, session.roomId)
        session.roomName = names.get(session.roomId, session.roomName)

    # A plenary line copied into several rooms' tables happens in the Main room.
    main_id = next((r.roomId for r in keepers if r.chairRole == "main"), None)
    if main_id:
        in_main = {
            (s.date, s.startTime, s.topicKey)
            for s in sessions
            if s.kind == "plenary" and s.roomId == main_id
        }
        sessions = [
            s for s in sessions
            if not (
                s.kind == "plenary"
                and s.roomId != main_id
                and (s.date, s.startTime, s.topicKey) in in_main
            )
        ]
    order = {room.roomId: room.order for room in keepers}
    sessions.sort(key=lambda s: (s.date, s.startTime, order.get(s.roomId, 0)))
    return keepers, sessions


def _minutes(hhmm: str) -> int:
    try:
        h, m = (hhmm or "0:0").split(":")[:2]
        return int(h) * 60 + int(m)
    except ValueError:
        return 0


def _codes_related(a: list[str], b: list[str]) -> bool:
    return any(x == y or x.startswith(f"{y}.") or y.startswith(f"{x}.") for x in a for y in b)


def _agrees(s: Session, other: list[Session]) -> bool:
    start, end = _minutes(s.startTime), _minutes(s.endTime)
    for o in other:
        if o.date != s.date:
            continue
        if min(end, _minutes(o.endTime)) <= max(start, _minutes(o.startTime)):
            continue
        if s.agendaItems and o.agendaItems:
            if _codes_related(s.agendaItems, o.agendaItems):
                return True
        elif s.topicKey and s.topicKey == o.topicKey:
            return True
    return False


def _names_similar(a: str | None, b: str | None) -> bool:
    x, y = norm_room(a or ""), norm_room(b or "")
    return bool(x and y) and (x in y or y in x)


def _schedule_twin(room: Room, candidates: list[Room], sessions: list[Session], current) -> Room | None:
    """Coloured room whose schedule clearly matches this name-only room's schedule."""
    mine = [s for s in sessions if current(s) == room.roomId and s.kind != "break"]
    if len(mine) < 3 or not candidates:
        return None
    scored = []
    for cand in candidates:
        theirs = [s for s in sessions if current(s) == cand.roomId]
        scored.append((sum(1 for s in mine if _agrees(s, theirs)) / len(mine), cand))
    scored.sort(key=lambda t: t[0], reverse=True)
    best, cand = scored[0]
    second = scored[1][0] if len(scored) > 1 else 0.0
    needed = 0.5 if _names_similar(room.roomName, cand.roomName) else 0.7
    return cand if best >= needed and best - second >= 0.25 else None
