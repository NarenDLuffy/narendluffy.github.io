"""RAN1 Live Draft Tracker.

Watches each meeting's public `Inbox/drafts/` tree (and, optionally, a
meeting-local source) and turns directory changes into normalized draft
artifacts and events mapped onto the canonical agenda items.
"""

from .tracker import ScanConfig, scan_meeting

__all__ = ["ScanConfig", "scan_meeting"]
