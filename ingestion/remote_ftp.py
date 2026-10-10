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
import json
import os
import urllib.request
from datetime import date, timedelta
from urllib.parse import quote, unquote, urlparse

INBOX_PATH = "/RAN1/Inbox/"
TIMEOUT = 30
APP_URL = os.environ.get("RAN1_APP_URL", "https://ran1.app")

_conns: dict[str, ftplib.FTP] = {}


def in_meeting_week(start: str | None, end: str | None, today: date | None = None) -> bool:
    try:
        s, e = date.fromisoformat(start or ""), date.fromisoformat(end or "")
    except ValueError:
        return False
    t = today or date.today()
    return s - timedelta(days=1) <= t <= e + timedelta(days=1)


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


def remote_root(meeting_id: str, start: str | None, end: str | None) -> str | None:
    """ftp://host/RAN1/Inbox/ when the remote FTP should be used now."""
    if not in_meeting_week(start, end) or not credentials():
        return None
    host = host_for(meeting_id)
    if not host or _connect(host) is None:
        return None
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
