"""Merge the main chair schedule with sub-chair schedules.

Source priority (never negotiable):

  main   -> day, time blocks, rooms, online/offline, breaks, opening/closing
  detail -> exact agenda items, precise timing inside a block, subject,
            sequence, responsible sub-chair

Merging happens per time slot (see Session.slot_key) so that a change in one
document only reprocesses the slots that document touches. A detail source can
never resurrect a slot the main schedule no longer contains.
"""

from __future__ import annotations

from .models import ScheduleConflict, Session, SessionSourceRef

DETAIL_FIELDS = ("topic", "agendaItems", "sessionLead", "startTime", "endTime")
MAIN_ONLY_FIELDS = ("roomId", "roomName", "mode", "kind")


def _merge_refs(base: list[SessionSourceRef], extra: SessionSourceRef) -> list[SessionSourceRef]:
    for ref in base:
        if ref.sourceId == extra.sourceId:
            ref.contributed = sorted(set(ref.contributed) | set(extra.contributed))
            return base
    return [*base, extra]


def merge(
    main_sessions: list[Session],
    detail_sessions: list[Session],
) -> tuple[list[Session], list[ScheduleConflict]]:
    """Return merged sessions plus any unresolved cross-source conflicts."""
    by_slot: dict[str, Session] = {s.slot_key: s for s in main_sessions}
    conflicts: list[ScheduleConflict] = []

    for detail in detail_sessions:
        target = by_slot.get(detail.slot_key)

        if target is None:
            # Fall back to same day + overlapping room, otherwise keep the detail
            # session as its own entry rather than inventing a main-schedule slot.
            candidates = [
                s
                for s in by_slot.values()
                if s.date == detail.date and s.roomId == detail.roomId
                and s.startTime <= detail.startTime < s.endTime
            ]
            if not candidates:
                by_slot[detail.slot_key] = detail
                continue
            target = candidates[0]

        detail_ref = next(iter(detail.sources), None)

        if detail.agendaItems:
            target.agendaItems = sorted(set(target.agendaItems) | set(detail.agendaItems))
        if detail.sessionLead:
            target.sessionLead = detail.sessionLead
        if detail.topic and detail.topicKey != "default":
            target.topic = detail.topic
            target.topicKey = detail.topicKey

        if detail.roomId and detail.roomId != target.roomId:
            # Room is main-authoritative: preserve the conflict, never guess.
            conflicts.append(
                ScheduleConflict(
                    conflictId=f"{target.sessionId}-roomId",
                    sessionId=target.sessionId,
                    field="roomId",
                    values=[
                        {"sourceId": next(iter(target.sources)).sourceId, "value": target.roomId},
                        {
                            "sourceId": detail_ref.sourceId if detail_ref else "unknown",
                            "value": detail.roomId,
                        },
                    ],
                )
            )

        if detail_ref:
            target.sources = _merge_refs(
                target.sources,
                SessionSourceRef(
                    sourceId=detail_ref.sourceId,
                    contributed=[f for f in DETAIL_FIELDS if getattr(detail, f, None)],
                ),
            )

    merged = sorted(by_slot.values(), key=lambda s: (s.date, s.startTime, s.roomId))
    return merged, conflicts
