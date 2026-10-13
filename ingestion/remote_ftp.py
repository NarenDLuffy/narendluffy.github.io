"""Remote meeting FTP (e.g. RAN-Maastricht.3gpp.org).

During the meeting week 3GPP exposes the venue documents over FTP to delegates
*outside* the venue network — which is where GitHub Actions runs. Its layout
mirrors Meetings_3GPP_SYNC, so documents live under RAN1/Inbox/.

* The host differs per meeting and is entered by a delegate in the app; it is
  read back from the app's public endpoint. No host is ever guessed.
* Credentials come from MEETING_FTP_USER / MEETING_FTP_PASS (GitHub secrets).
* Used only from start−1 day to end+1 day. Every failure is silent: the other
  sources keep working.

Files are addressed as ftp://<host>/<path>; `fetch_bytes` downloads them.
"""

from __future__ import annotations

import ftplib
import io
import json
import os
import re
import urllib.request
from datetime import date, timedelta
from urllib.parse import quote, unquote, urlparse

INBOX_PATH = "/RAN1/Inbox/"
TIMEOUT = 30
APP_URL = os.environ.get("RAN1_APP_URL", "https://ran1.app")

_conns: dict[str, ftplib.FTP] = {}

# What the last remote-source decision was, per meeting, for the health record.
_status: dict[str, dict] = {}
# Hosts read out of the meeting's own documents and verified by a real login.
_detected: dict[str, str] = {}

# The venue's remote FTP address, as printed in the meeting's own documents.
# Never guessed: a candidate only counts when the saved login works there.
HOST_RE = re.compile(r"\b(RAN-[A-Za-z0-9][A-Za-z0-9-]*\.3gpp\.org)\b", re.I)
VENUE_HINTS = (
    "venue",
    "floorplan",
    "floor plan",
    "logistic",
    "information",
    "invitation",
    "arrival",
)
MAX_HOST_DOCS = 6
MAX_HOST_DOC_BYTES = 4 * 1024 * 1024


def meeting_phase(start: str | None, end: str | None, today: date | None = None) -> str:
    """Which folders to read: one rule shared by the timetable and drafts.

    before — the meeting folder only (Meetings Sync still holds the last meeting);
    edge   — the day before the meeting: Meetings Sync AND the meeting folder;
    week   — the meeting days: Meetings Sync only (plus the venue copy);
    after  — from the day after: Meetings Sync AND the meeting folder.
    """
    try:
        s, e = date.fromisoformat(start or ""), date.fromisoformat(end or "")
    except ValueError:
        return "before"
    t = today or date.today()
    if s <= t <= e:
        return "week"
    if t == s - timedelta(days=1):
        return "edge"
    return "before" if t < s else "after"


def in_meeting_week(start: str | None, end: str | None, today: date | None = None) -> bool:
    """Live trees count: the day before, the meeting days and the day after."""
    t = today or date.today()
    try:
        e = date.fromisoformat(end or "")
    except ValueError:
        return False
    return meeting_phase(start, end, today) in ("week", "edge") or (
        meeting_phase(start, end, today) == "after" and t <= e + timedelta(days=1)
    )


def credentials() -> tuple[str, str] | None:
    user, pw = os.environ.get("MEETING_FTP_USER"), os.environ.get("MEETING_FTP_PASS")
    return (user, pw) if user and pw else None


def host_for(meeting_id: str) -> str | None:
    """The host a delegate entered for this meeting, or None."""
    override = os.environ.get("MEETING_FTP_HOST")
    if override:
        return override
    try:
        url = f"{APP_URL}/api/public/meeting-ftp-host?meeting={quote(meeting_id)}"
        with urllib.request.urlopen(url, timeout=15) as res:
            return json.loads(res.read().decode()).get("host") or None
    except Exception as exc:
        print(f"  remote FTP host lookup failed: {exc}")
        return None


def snapshot(meeting_id: str) -> dict:
    """What the last remote-source decision was, for the health record."""
    snap = dict(_status.get(meeting_id) or {})
    snap.setdefault("credentials", bool(credentials()))
    return snap


def _note(meeting_id: str, state: str, host: str | None = None) -> None:
    _status[meeting_id] = {"state": state, "host": host, "credentials": bool(credentials())}


def remote_root(meeting_id: str, start: str | None, end: str | None) -> str | None:
    """ftp://host/RAN1/Inbox/ when the remote FTP should be used now."""
    if not credentials():
        _note(meeting_id, "skipped-no-credentials")
        return None
    if not in_meeting_week(start, end):
        _note(meeting_id, "outside-meeting-week")
        return None
    host = host_for(meeting_id) or detected_host(meeting_id)
    if not host:
        _note(meeting_id, "skipped-no-host")
        return None
    if _connect(host) is None:
        _note(meeting_id, "unreachable", host)
        return None
    _note(meeting_id, "read", host)
    return f"ftp://{host}{INBOX_PATH}"


def _connect(host: str) -> ftplib.FTP | None:
    if host in _conns:
        try:
            _conns[host].voidcmd("NOOP")
            return _conns[host]
        except Exception:
            _conns.pop(host, None)
    creds = credentials()
    if not creds:
        return None
    for cls in (ftplib.FTP_TLS, ftplib.FTP):
        try:
            ftp = cls(host, timeout=TIMEOUT)
            ftp.login(*creds)
            if isinstance(ftp, ftplib.FTP_TLS):
                ftp.prot_p()
            ftp.set_pasv(True)
            _conns[host] = ftp
            return ftp
        except Exception:
            continue
    print(f"  remote FTP {host} unreachable")
    return None


def _split(url: str) -> tuple[str, str]:
    p = urlparse(url)
    return p.hostname or "", unquote(p.path or "/")


def list_dir(url: str) -> list[tuple[str, str, bool, str | None, int | None]]:
    """(name, url, is_dir, modified ISO, size) children of a remote folder."""
    host, path = _split(url)
    ftp = _connect(host)
    if ftp is None:
        return []
    base = url if url.endswith("/") else url + "/"
    out: list[tuple[str, str, bool, str | None, int | None]] = []
    try:
        for name, facts in ftp.mlsd(path):
            if name in (".", ".."):
                continue
            is_dir = facts.get("type") == "dir"
            m = facts.get("modify")
            iso = f"{m[0:4]}-{m[4:6]}-{m[6:8]}T{m[8:10]}:{m[10:12]}:00Z" if m and len(m) >= 12 else None
            size = int(facts["size"]) if facts.get("size", "").isdigit() else None
            out.append((name, base + quote(name) + ("/" if is_dir else ""), is_dir, iso, size))
        return out
    except Exception:
        pass
    try:  # servers without MLSD: NLST, directories detected by cwd
        for name in ftp.nlst(path):
            name = name.rstrip("/").rsplit("/", 1)[-1]
            if name in (".", ".."):
                continue
            try:
                ftp.cwd(path.rstrip("/") + "/" + name)
                is_dir = True
            except Exception:
                is_dir = False
            out.append((name, base + quote(name) + ("/" if is_dir else ""), is_dir, None, None))
    except Exception:
        return []
    return out


def walk_files(root: str, max_depth: int = 4) -> list[tuple[str, str]]:
    """(url, name) of every file under root, recursively."""
    found: list[tuple[str, str]] = []

    def walk(url: str, depth: int) -> None:
        if depth > max_depth:
            return
        for name, child, is_dir, _m, _s in list_dir(url):
            if is_dir:
                walk(child, depth + 1)
            else:
                found.append((child, name))

    walk(root, 1)
    return found


def fetch_bytes(url: str, max_bytes: int = 12 * 1024 * 1024) -> bytes | None:
    host, path = _split(url)
    ftp = _connect(host)
    if ftp is None:
        return None
    chunks: list[bytes] = []
    total = 0

    def sink(b: bytes) -> None:
        nonlocal total
        total += len(b)
        if total > max_bytes:
            raise ValueError("too large")
        chunks.append(b)

    try:
        ftp.retrbinary(f"RETR {path}", sink)
    except Exception:
        return None
    return b"".join(chunks)


def detected_host(meeting_id: str) -> str | None:
    """A venue address already read from this meeting's documents, if any."""
    if meeting_id in _detected:
        return _detected[meeting_id]
    from . import health  # local import: health reads this module, never the reverse

    cached = health.cached_detected_host(meeting_id)
    if cached:
        _detected[meeting_id] = cached
    return cached


def _http_download(url: str, max_bytes: int) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ran1-live/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            data = res.read(max_bytes + 1)
        return data if len(data) <= max_bytes else None
    except Exception:
        return None


def _docx_text(data: bytes) -> str:
    """Active visible text of a .docx; empty when it cannot be read."""
    try:
        from docx import Document

        from .docx_active_text import active_element_text

        return active_element_text(Document(io.BytesIO(data)).element)
    except Exception:
        return ""


def _venue_candidates(docs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Documents most likely to print the venue's FTP address, cheapest first."""

    def score(item: tuple[str, str]) -> tuple[int, int]:
        name = item[0].lower()
        hint = next((i for i, h in enumerate(VENUE_HINTS) if h in name), len(VENUE_HINTS))
        return (hint, len(name))

    docs = [d for d in docs if d[1] and d[1].lower().endswith(".docx")]
    # Only probe documents whose name says it could carry the address — otherwise
    # every refresh would download six unrelated files looking for one string.
    hinted = [d for d in docs if any(h in d[0].lower() for h in VENUE_HINTS)]
    return sorted(hinted, key=score)[:MAX_HOST_DOCS]


def ensure_host(meeting_id: str, docs: list[tuple[str, str]]) -> str | None:
    """Find the venue's remote FTP address in the meeting's own documents.

    Never guessed: an address only counts when it is printed in a document the
    meeting itself published *and* the saved login actually works there. A
    verified address is remembered in the meeting's health record, so the
    delegates' one-time entry is only needed when no document states it.
    """
    cached = detected_host(meeting_id)
    if cached:
        return cached
    if not credentials():
        return None
    for name, url in _venue_candidates(docs):
        data = fetch_bytes(url) if url.startswith("ftp://") else _http_download(
            url, MAX_HOST_DOC_BYTES
        )
        if not data:
            continue
        for host in dict.fromkeys(HOST_RE.findall(_docx_text(data))):
            if _connect(host) is not None:
                _detected[meeting_id] = host
                from . import health

                health.remember_detected_host(meeting_id, host)
                print(f"  remote FTP host {host} read from {name} and login verified")
                return host
    return None
