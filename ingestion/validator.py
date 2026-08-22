"""Sanity checks that protect the published schedule.

Reliability rule: a failed or implausible parse must never replace a good
schedule. generate_schedule.py aborts the write when validate() fails.
"""

from __future__ import annotations

from .models import ScheduleBundle

MIN_SESSIONS = 5


def validate(bundle: ScheduleBundle, previous: dict | None = None) -> list[str]:
    errors: list[str] = []

    # A meeting whose schedule 3GPP has not published yet is legitimately empty:
    # it is published as metadata only (schedulePublished = false). Session and
    # room checks apply only once a schedule claims to exist.
    schedule_claimed = bundle.meeting.schedulePublished or bool(bundle.sessions)

    if schedule_claimed:
        if len(bundle.sessions) < MIN_SESSIONS:
            errors.append(f"only {len(bundle.sessions)} sessions parsed")

        if not bundle.rooms:
            errors.append("no rooms discovered")

    for s in bundle.sessions:
        if s.endTime <= s.startTime:
            errors.append(f"{s.sessionId}: end time not after start time")
        # Breaks and lunches are derived from the surrounding grid, so only
        # real sessions must carry document provenance.
        if not s.sources and s.kind not in ("break", "lunch"):
            errors.append(f"{s.sessionId}: missing source provenance")

    if previous:
        # Compare distinct slots, not raw rows: when several chairs circulate
        # copies of the same week grid, deduplicating them legitimately reduces
        # the row count without losing any actual session.
        def slots(items) -> set[tuple]:
            return {
                (i.get("date"), i.get("startTime"), i.get("endTime"), i.get("topic"))
                for i in items
            }

        before = slots(previous.get("sessions", []))
        after = slots(s.to_json() for s in bundle.sessions)
        if before and len(after) < len(before) * 0.5:
            errors.append(
                f"session coverage collapsed from {len(before)} to {len(after)} slots; refusing publish"
            )

    return errors
