from ingestion.models import Room, Session
from ingestion.room_resolver import resolve_rooms

M = "m"


def room(rid, name, lane):
    return Room(roomId=rid, meetingId=M, roomName=name, order=0, shortName=name, chairLaneId=lane)


def sess(rid, t, code):
    h = int(t[:2])
    return Session(sessionId=f"{rid}{t}{code}", meetingId=M, date="2026-10-12", day="Mon",
                   startTime=t, endTime=f"{h+1:02d}:00", roomId=rid, roomName="", topic=code,
                   topicKey=code, agendaItems=[code])


def base():
    rooms = [room("a", "Hall A", f"{M}:online:D9D9D9"), room("b", "Hall B", f"{M}:online:FFD966")]
    s = [sess("a", t, c) for t, c in [("09:00", "9.1"), ("10:00", "9.2"), ("11:00", "9.3"), ("12:00", "9.4")]]
    s += [sess("b", t, c) for t, c in [("09:00", "10.1"), ("10:00", "10.5.4"), ("11:00", "10.3"), ("12:00", "10.4")]]
    return rooms, s


def test_same_schedule_merges():
    rooms, s = base()
    rooms.append(room("x", "Other A", f"{M}:name:x"))
    s += [sess("x", t, c) for t, c in [("09:00", "9.1"), ("10:00", "9.2"), ("11:00", "9.3")]]
    kept, _ = resolve_rooms(M, rooms, s)
    assert {r.roomId for r in kept} == {"a", "b"}


def test_finer_split_merges():
    rooms, s = base()
    rooms.append(room("y", "Hall B 1F", f"{M}:name:y"))
    s += [sess("y", t, c) for t, c in [("09:00", "10.1"), ("10:00", "10.5.4.1"), ("11:00", "10.3.2")]]
    kept, _ = resolve_rooms(M, rooms, s)
    assert {r.roomId for r in kept} == {"a", "b"}


def test_unrelated_room_kept():
    rooms, s = base()
    rooms.append(room("z", "Z", f"{M}:name:z"))
    s += [sess("z", t, c) for t, c in [("09:00", "11.1"), ("10:00", "11.2"), ("11:00", "11.3")]]
    kept, _ = resolve_rooms(M, rooms, s)
    assert "z" in {r.roomId for r in kept}


def test_ambiguous_tie_kept():
    rooms, s = base()
    rooms.append(room("t", "T", f"{M}:name:t"))
    s += [sess("a", "14:00", "12.1"), sess("b", "14:00", "12.1")]
    s += [sess("t", t, c) for t, c in [("14:00", "12.1"), ("15:00", "13.1"), ("16:00", "13.2")]]
    kept, _ = resolve_rooms(M, rooms, s)
    assert "t" in {r.roomId for r in kept}
