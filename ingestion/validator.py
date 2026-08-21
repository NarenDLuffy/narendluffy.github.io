"""Sanity checks that protect the published schedule.

Reliability rule: a failed or implausible parse must never replace a good
schedule. generate_schedule.py aborts the write when validate() fails.
"""

from __future__ import annotations

from .models import ScheduleBundle

MIN_SESSIONS = 5


def validate(bundle: ScheduleBundle, previous: dict | None = None) -> list[str]:
    errors: list[str] = []

    if len(bundle.sessions) < MIN_SESSIONS:
        errors.append(f"only {len(bundle.sessions)} sessions parsed")

    if not bundle.rooms:
        errors.append("no rooms discovered")

    for s in bundle.sessions:
        if s.endTime <= s.startTime:
            errors.append(f"{s.sessionId}: end time not after start time")
        if not s.sources:
            errors.append(f"{s.sessionId}: missing source provenance")

    if previous:
        before = len(previous.get("sessions", []))
        if before and len(bundle.sessions) < before * 0.5:
            errors.append(
                f"session count collapsed from {before} to {len(bundle.sessions)}; refusing publish"
            )

    return errors
