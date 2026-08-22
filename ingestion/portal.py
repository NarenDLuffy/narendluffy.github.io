"""Live meeting discovery from the official 3GPP portal meeting service.

The portal page https://portal.3gpp.org/?tbid=373&SubTB=379 is backed by a REST
service that returns every meeting of a technical body, with authoritative
dates, location, country and timezone. RAN1 is technical body 379.

Nothing here is specific to a single meeting: whatever the service returns is
published, so future meetings appear automatically.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, available_timezones

import requests

MEETINGS_ENDPOINT = "https://portal.3gpp.org/webservices/Rest/Meetings.svc/GetMeetings"
RAN1_TB_ID = 379
FTP_ROOT = "https://www.3gpp.org/ftp/tsg_ran/WG1_RL1"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)
TITLE_RE = re.compile(r"RAN1#(?P<number>\d+)(?P<suffix>[-\s]?bis)?", re.I)

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Referer": "https://portal.3gpp.org/"})


@dataclass
class PortalMeeting:
    """One meeting exactly as the portal describes it."""

    portal_id: int
    name: str
    number: int
    type: str
    start_date: str
    end_date: str
    timezone: str
    city: str | None
    country: str | None
    folder_url: str | None
    raw: dict[str, Any]

    @property
    def slug(self) -> str:
        return f"ran1-{self.number}-bis" if self.type == "bis" else f"ran1-{self.number}"


def fetch_meetings(start: str, end: str) -> list[PortalMeeting]:
    """Every RAN1 meeting the portal knows about in the given window."""
    payload = {
        "getMeetingsInput": {
            "StartRow": 0,
            "ResultsPerPage": 200,
            "SortBy": "Date",
            "SortAscending": True,
            "StartDate": f"{start} 00:00:00",
            "EndDate": f"{end} 00:00:00",
            "Tbs": [RAN1_TB_ID],
            "IncludeChildTbs": False,
            "IncludeNonTBMeetings": False,
            "Reference": "",
            "Registered": False,
        }
    }
    response = _session.post(MEETINGS_ENDPOINT, json=payload, timeout=45)
    response.raise_for_status()
    return [m for m in (_to_meeting(row) for row in response.json()) if m]


def _to_meeting(row: dict[str, Any]) -> PortalMeeting | None:
    title = (row.get("Title") or row.get("ShortTitle") or "").strip()
    match = TITLE_RE.search(title.replace("3GPP", "3GPP "))
    if not match:
        return None  # training sessions, social events, other technical bodies
    number = int(match.group("number"))
    kind = "bis" if match.group("suffix") else "regular"
    return PortalMeeting(
        portal_id=int(row["Id"]),
        name=f"RAN1#{number}-bis" if kind == "bis" else f"RAN1#{number}",
        number=number,
        type=kind,
        start_date=str(row["StartDate"])[:10],
        end_date=str(row["EndDate"])[:10],
        timezone=resolve_timezone(row.get("StartTimeZone")),
        city=_clean_location(row.get("Location")),
        country=row.get("Country") or None,
        folder_url=_https_folder(row.get("MtgDocURL")),
        raw=row,
    )


def _clean_location(location: str | None) -> str | None:
    if not location or location.lower() in {"none", "online", "tbd"}:
        return None
    return re.sub(r"\s+Metropolitan Area$", "", location).strip() or None


def _https_folder(url: str | None) -> str | None:
    if not url:
        return None
    folder = url.replace("https://ftp.3gpp.org/", "https://www.3gpp.org/ftp/")
    folder = folder.replace("http://ftp.3gpp.org/", "https://www.3gpp.org/ftp/")
    return folder if folder.endswith("/") else folder + "/"


# --- timezone resolution -----------------------------------------------------
# The portal reports Windows-style labels such as "(GMT+09:00) Seoul". The city
# names inside are matched against the IANA database, so new host cities resolve
# without a lookup table.
_ZONES_BY_CITY: dict[str, str] = {}
for _zone in available_timezones():
    _ZONES_BY_CITY.setdefault(_zone.rsplit("/", 1)[-1].replace("_", " ").lower(), _zone)

OFFSET_RE = re.compile(r"GMT([+-])(\d{1,2})[:.](\d{2})", re.I)


def resolve_timezone(label: str | None, fallback: str = "UTC") -> str:
    if not label:
        return fallback
    cities = label.split(")", 1)[-1]
    for city in [c.strip().lower() for c in cities.split(",") if c.strip()]:
        zone = _ZONES_BY_CITY.get(city)
        if zone:
            return zone
    # No known city: fall back to any zone currently at the stated offset.
    m = OFFSET_RE.search(label)
    if m:
        sign = 1 if m.group(1) == "+" else -1
        wanted = sign * (int(m.group(2)) * 3600 + int(m.group(3)) * 60)
        now = datetime.now(timezone.utc)
        for zone in sorted(available_timezones()):
            try:
                offset = now.astimezone(ZoneInfo(zone)).utcoffset()
            except Exception:  # pragma: no cover - defensive
                continue
            if offset is not None and int(offset.total_seconds()) == wanted:
                return zone
    return fallback


# --- meeting folder contents -------------------------------------------------

HREF_RE = re.compile(r'href="(?P<href>[^"]+)"', re.I)


def list_folder(url: str) -> list[str]:
    """File and folder URLs inside a 3GPP directory listing."""
    try:
        response = _session.get(url, timeout=45)
        response.raise_for_status()
    except requests.RequestException:
        return []
    entries: list[str] = []
    for m in HREF_RE.finditer(response.text):
        href = m.group("href")
        if href.startswith("?") or "/ftp/" not in href:
            continue
        absolute = href if href.startswith("http") else "https://www.3gpp.org" + href
        if absolute.rstrip("/") != url.rstrip("/") and absolute.startswith(url):
            entries.append(absolute)
    return sorted(set(entries))


def fetch_agenda_csv(folder_url: str) -> list[tuple[str, str]]:
    """(code, title) rows from the meeting's published agenda.csv, if any."""
    try:
        response = _session.get(f"{folder_url}Agenda/agenda.csv", timeout=45)
        if response.status_code != 200 or not response.text.strip():
            return []
    except requests.RequestException:
        return []
    rows: list[tuple[str, str]] = []
    for row in csv.reader(io.StringIO(response.text)):
        if len(row) >= 2 and row[0].strip():
            rows.append((row[0].strip(), row[1].strip()))
    return rows
