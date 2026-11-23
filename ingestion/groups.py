"""Working groups the app follows (RAN1, RAN2, RAN3).

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
    #: "single_grid": one schedule DOCX per meeting (RAN2); "chair_files": RAN1;
    #: "chair_notes_plus_sheet": chair-notes weekday table + offline XLSX (RAN3);
    #: "time_plan": RAN Plenary chair time plan DOCX; "pptx_slides": RAN4 schedule slides;
    #: "session_plan": SA2 convenors' session plan DOCX.
    schedule_style: str

    @property
    def sync_root(self) -> str:
        return f"https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/{self.sync_name}/"


GROUPS: dict[str, WorkingGroup] = {
    "RAN1": WorkingGroup("RAN1", 379, "ran1", "RAN1", "chair_files"),
    "RAN2": WorkingGroup("RAN2", 380, "ran2", "RAN2", "single_grid"),
    "RAN3": WorkingGroup("RAN3", 381, "ran3", "RAN3", "chair_notes_plus_sheet"),
    #: TSG RAN plenary: "RAN#<n> time plan vNN" in Inbox/Chair (ranp_schedule.py).
    #: RAN4: "RAN4_<n>_meeting_schedule_vNN.pptx" in Inbox/Meeting_Arrangements (ran4_schedule.py).
    "RAN4": WorkingGroup("RAN4", 382, "ran4", "RAN4", "pptx_slides"),
    "RAN": WorkingGroup("RAN", 373, "ran", "RAN", "time_plan"),
    #: SA2: "S2-…_SA2-<n>-Session Plan - rNN.docx" in Inbox/Drafts/_Session_Plan_Updates (sa2_schedule.py).
    "SA2": WorkingGroup("SA2", 385, "sa2", "SA2", "session_plan"),
}


def group_for(slug_or_id: str | None) -> WorkingGroup:
    """The group a meeting slug/id belongs to ("ran2-136" -> RAN2); RAN1 by default."""
    text = (slug_or_id or "").lower()
    for group in GROUPS.values():
        if text.startswith(group.slug_prefix + "-"):
            return group
    return GROUPS["RAN1"]
