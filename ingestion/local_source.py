"""Meeting-local schedule source (venue network only).

During a physical RAN1 meeting, the 3GPP meeting network serves documents from

    http://10.10.10.10/ftp/RAN/RAN1/Inbox/

which is frequently fresher than the public 3GPP site. Two hard rules:

1. The PUBLIC source is the default and the only source GitHub Actions uses.
   Hosted runners cannot reach RFC1918 addresses; never make a build depend
   on 10.x connectivity.
2. Anything produced from the local server keeps its own provenance and is
   labelled "Meeting-local source" so a delegate can always tell where a
   session came from and which document version produced it.

This module is intended for a delegate running the pipeline from a laptop on
the venue network (`python -m ingestion.generate_schedule --source local`),
or for a small on-site relay that publishes schedule.json back to the app.
"""

from __future__ import annotations

from dataclasses import dataclass

LOCAL_BASE_URL = "http://10.10.10.10/ftp/RAN/RAN1/Inbox/"
PUBLIC_BASE_URL = "https://www.3gpp.org/ftp/tsg_ran/WG1_RL1"
PROBE_TIMEOUT_SECONDS = 3


@dataclass
class SourceEndpoint:
    origin: str  # "public" | "meeting-local"
    base_url: str
    label_suffix: str = ""


PUBLIC_ENDPOINT = SourceEndpoint("public", PUBLIC_BASE_URL)
LOCAL_ENDPOINT = SourceEndpoint("meeting-local", LOCAL_BASE_URL, " (meeting-local)")


def is_local_reachable(timeout: int = PROBE_TIMEOUT_SECONDS) -> bool:
    """Cheap reachability probe; always False on GitHub-hosted runners."""
    try:
        import requests

        return requests.head(LOCAL_BASE_URL, timeout=timeout).ok
    except Exception:
        return False


def select_endpoints(prefer_local: bool = True) -> list[SourceEndpoint]:
    """Public first, then local only when it actually answers."""
    endpoints = [PUBLIC_ENDPOINT]
    if prefer_local and is_local_reachable():
        endpoints.append(LOCAL_ENDPOINT)
    return endpoints


def label_for(base_label: str, endpoint: SourceEndpoint) -> str:
    return f"{base_label}{endpoint.label_suffix}"
