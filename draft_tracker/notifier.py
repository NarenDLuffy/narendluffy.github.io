"""Group raw draft events into user-facing notification payloads.

Notifications are produced from normalized events (never from raw directory
timestamps) and are grouped per agenda item and time bucket so a burst of
uploads becomes "10.8.1 has 4 new updates" instead of four separate pings.

Delivery is the client's job (in-app now, PWA push later); this module only
produces the content, which never exposes internal file IDs.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from .models import DraftEvent

IMPORTANT = {"FL_SUMMARY_UPDATED", "NEW_ROUND"}


def _bucket(iso: str, minutes: int) -> str:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    floored = dt - timedelta(minutes=dt.minute % minutes, seconds=dt.second)
    return floored.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def group_events(events: list[DraftEvent], window_minutes: int = 10) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[DraftEvent]] = defaultdict(list)
    for event in events:
        grouped[(event.agendaItemId or "unmapped", _bucket(event.detectedAt, window_minutes))].append(
            event
        )

    notifications: list[dict[str, Any]] = []
    for (agenda, bucket), items in grouped.items():
        counts: dict[str, int] = defaultdict(int)
        for item in items:
            counts[item.eventType] += 1
        notifications.append(
            {
                "agendaItemId": None if agenda == "unmapped" else agenda,
                "bucketAt": bucket,
                "detectedAt": max(i.detectedAt for i in items),
                "total": len(items),
                "counts": dict(counts),
                "important": any(i.eventType in IMPORTANT for i in items),
                "eventIds": [i.id for i in items],
                "summary": summarize(counts),
            }
        )
    return sorted(notifications, key=lambda n: n["detectedAt"], reverse=True)


def summarize(counts: dict[str, int]) -> str:
    parts: list[str] = []
    labels = {
        "NEW_FILE": ("new file", "new files"),
        "FILE_UPDATED": ("draft update", "draft updates"),
        "FL_SUMMARY_UPDATED": ("FL summary update", "FL summary updates"),
        "NEW_ROUND": ("new round", "new rounds"),
        "NEW_FOLDER": ("new folder", "new folders"),
        "FILE_REMOVED": ("removed file", "removed files"),
    }
    for key, (one, many) in labels.items():
        n = counts.get(key, 0)
        if n:
            parts.append(f"{n} {one if n == 1 else many}")
    return ", ".join(parts) or "no changes"
