"""Working groups the app follows (RAN1, RAN2).

Everything group-specific lives here: the 3GPP portal technical body, the
display/slug prefix, the Meetings Sync folder and the schedule reader. The rest
of the pipeline takes a group from a meeting's slug and never names one.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkingGroup:
    key: str  # "RAN1"
    tb_id: int  # 3GPP portal technical body
    slug_prefix: str  # "ran1"
    #: Folder name under /ftp/Meetings_3GPP_SYNC/ and on the venue server.
    sync_name: str
    #: "single_grid": one schedule DOCX per meeting (RAN2); "chair_files": RAN1.
    schedule_style: str

    @property
    def sync_root(self) -> str:
        return f"https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/{self.sync_name}/"


GROUPS: dict[str, WorkingGroup] = {
    "RAN1": WorkingGroup("RAN1", 379, "ran1", "RAN1", "chair_files"),
    "RAN2": WorkingGroup("RAN2", 380, "ran2", "RAN2", "single_grid"),
}


def group_for(slug_or_id: str | None) -> WorkingGroup:
    """The group a meeting slug/id belongs to ("ran2-136" -> RAN2); RAN1 by default."""
    text = (slug_or_id or "").lower()
    for group in GROUPS.values():
        if text.startswith(group.slug_prefix + "-"):
            return group
    return GROUPS["RAN1"]
