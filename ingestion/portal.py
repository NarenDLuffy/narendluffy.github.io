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
from typing import Any
from zoneinfo import available_timezones

import requests

MEETINGS_ENDPOINT = "https://portal.3gpp.org/webservices/Rest/Meetings.svc/GetMeetings"
RAN1_TB_ID = 379
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
    group: str = "RAN1"

    @property
    def slug(self) -> str:
        prefix = self.group.lower()
        return f"{prefix}-{self.number}-bis" if self.type == "bis" else f"{prefix}-{self.number}"


def fetch_meetings(start: str, end: str, group: str = "RAN1") -> list[PortalMeeting]:
    """Every meeting of one working group the portal knows about in the window."""
    from .groups import GROUPS

    wg = GROUPS[group]
    payload = {
        "getMeetingsInput": {
            "StartRow": 0,
            "ResultsPerPage": 200,
            "SortBy": "Date",
            "SortAscending": True,
            "StartDate": f"{start} 00:00:00",
            "EndDate": f"{end} 00:00:00",
            "Tbs": [wg.tb_id],
            "IncludeChildTbs": False,
            "IncludeNonTBMeetings": False,
            "Reference": "",
            "Registered": False,
        }
    }
    response = _session.post(MEETINGS_ENDPOINT, json=payload, timeout=45)
    response.raise_for_status()
    return [m for m in (_to_meeting(row, group) for row in response.json()) if m]


def _to_meeting(row: dict[str, Any], group: str = "RAN1") -> PortalMeeting | None:
    title = (row.get("Title") or row.get("ShortTitle") or "").strip()
    title_re = re.compile(TITLE_RE.pattern.replace("RAN1", re.escape(group)), re.I)
    match = title_re.search(title.replace("3GPP", "3GPP "))
    if not match:
        return None  # training sessions, social events, other technical bodies
    number = int(match.group("number"))
    kind = "bis" if match.group("suffix") else "regular"
    return PortalMeeting(
        portal_id=int(row["Id"]),
        name=f"{group}#{number}-bis" if kind == "bis" else f"{group}#{number}",
        number=number,
        type=kind,
        start_date=str(row["StartDate"])[:10],
        end_date=str(row["EndDate"])[:10],
        timezone=resolve_timezone(row.get("StartTimeZone")),
        city=_clean_location(row.get("Location")),
        country=row.get("Country") or None,
        folder_url=_https_folder(row.get("MtgDocURL")),
        raw=row,
        group=group,
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
    folder = folder if folder.endswith("/") else folder + "/"
    # RAN2's portal entries point at the Docs/ sub-folder; the meeting folder is its parent.
    return re.sub(r"Docs/$", "", folder, flags=re.I)


# --- timezone resolution -----------------------------------------------------
# The portal reports Windows-style labels such as "(GMT+09:00) Seoul". The city
# names inside are matched against the IANA database, so new host cities resolve
# without a lookup table; otherwise the stated fixed offset is used.
_ZONES_BY_CITY: dict[str, str] = {}
for _zone in sorted(available_timezones()):
    _ZONES_BY_CITY.setdefault(_zone.rsplit("/", 1)[-1].replace("_", " ").lower(), _zone)

OFFSET_RE = re.compile(r"GMT([+-])(\d{1,2})[:.](\d{2})", re.I)


# Windows zone labels whose cities are not IANA names but which observe DST.
_WINDOWS_ZONES = {
    "central time": "America/Chicago",
    "eastern time": "America/New_York",
    "mountain time": "America/Edmonton",
    "pacific time": "America/Los_Angeles",
    "atlantic time": "America/Halifax",
}


def resolve_timezone(label: str | None, fallback: str = "UTC") -> str:
    if not label:
        return fallback
    lowered = label.lower()
    for key, zone in _WINDOWS_ZONES.items():
        if key in lowered:
            return zone
    cities = label.split(")", 1)[-1]
    for city in [c.strip().lower() for c in cities.split(",") if c.strip()]:
        zone = _ZONES_BY_CITY.get(city)
        if zone:
            return zone
    m = OFFSET_RE.search(label)
    if m:
        hours, minutes = int(m.group(2)), int(m.group(3))
        if minutes == 0:
            if hours == 0:
                return "UTC"
            # Etc/GMT signs are inverted by POSIX convention.
            return f"Etc/GMT{'-' if m.group(1) == '+' else '+'}{hours}"
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
