"""Diff the newly parsed schedule against the last published one."""

from __future__ import annotations

from datetime import datetime, timezone

from .models import ScheduleBundle, ScheduleChange


def _key(session: dict) -> str:
    return f"{session['date']}|{session['topic']}|{'/'.join(session.get('agendaItems', []))}"


def detect_changes(previous: dict | None, bundle: ScheduleBundle) -> list[ScheduleChange]:
    if not previous:
        return []

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    old = {_key(s): s for s in previous.get("sessions", [])}
    new = {_key(s): s for s in bundle.to_json()["sessions"]}
    changes: list[ScheduleChange] = []

    def add(change_type: str, title: str, detail: str, session: dict, **kw) -> None:
        changes.append(
            ScheduleChange(
                changeId=f"{change_type}-{session['sessionId']}-{now}",
                meetingId=bundle.meeting.id,
                detectedAt=now,
                type=change_type,
                title=title,
                detail=detail,
                agendaItems=session.get("agendaItems", []),
                sessionId=session["sessionId"],
                sourceIds=[r["sourceId"] for r in session.get("sources", [])],
                **kw,
            )
        )

    for key, session in new.items():
        before = old.get(key)
        if before is None:
            add("session_added", f"{session['topic']} added", "New session in the schedule", session,
                to=f"{session['roomName']} {session['startTime']}-{session['endTime']}")
            continue
        if before["roomId"] != session["roomId"]:
            add("room_changed", f"{session['topic']} moved", "Session changed room", session,
                from_=before["roomName"], to=session["roomName"])
        if before["startTime"] != session["startTime"]:
            add("start_time_changed", f"{session['topic']} start time changed", "Start time changed",
                session, from_=before["startTime"], to=session["startTime"])
        if before["endTime"] != session["endTime"]:
            add("end_time_changed", f"{session['topic']} end time changed", "End time changed",
                session, from_=before["endTime"], to=session["endTime"])
        added_items = set(session.get("agendaItems", [])) - set(before.get("agendaItems", []))
        if added_items:
            add("agenda_item_added", f"AI {', '.join(sorted(added_items))} added",
                "Agenda item added to session", session, to=session["roomName"])

    for key, session in old.items():
        if key not in new:
            add("session_removed", f"{session['topic']} removed", "Session no longer in schedule",
                session, from_=session["roomName"])

    return changes
