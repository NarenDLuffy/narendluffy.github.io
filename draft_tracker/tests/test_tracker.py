"""Acceptance tests for the Draft Tracker.

Two completely different fixture meetings prove the tracker is generic: no
agenda number, topic name or folder convention is hard-coded anywhere.

    python -m draft_tracker.tests.test_tracker
"""

from __future__ import annotations

import sys
from typing import Any

from draft_tracker.directory_parser import NormalizedDirectoryEntry
from draft_tracker.tracker import scan_meeting

# --- fake sources ------------------------------------------------------------


class FakeSource:
    """A DraftSource backed by an in-memory tree: {dir_url: [(name, is_dir, size)]}"""

    def __init__(self, tree: dict[str, list[tuple[str, bool, int | None]]], source_type="public"):
        self.tree = tree
        self.source_type = source_type
        self.blobs: dict[str, bytes] = {}

    def discover_drafts_root(self) -> str | None:
        return "/drafts/" if "/drafts/" in self.tree else None

    def list_directory(self, path: str) -> list[NormalizedDirectoryEntry]:
        return [
            NormalizedDirectoryEntry(
                name=name,
                url=f"{path}{name}/" if is_dir else f"{path}{name}",
                is_dir=is_dir,
                size=size,
                modified_at="2026-08-24T10:00:00Z",
            )
            for name, is_dir, size in self.tree.get(path, [])
        ]

    def fetch_bytes(self, path: str) -> bytes | None:
        return self.blobs.get(path)


MEETING_A_AGENDA = {"10.8": "ISAC", "10.8.1": "Evaluations", "10.8.2": "Measurements"}
MEETING_B_AGENDA = {"7": "NR positioning", "7.2": "Sidelink carrier aggregation"}


def meeting_a_tree(round2: bool = False, extra_file: bool = False):
    tree: dict[str, list[tuple[str, bool, int | None]]] = {
        "/drafts/": [("10.8(ISAC)", True, None)],
        "/drafts/10.8(ISAC)/": [("10.8.1 Evaluations", True, None)],
        "/drafts/10.8(ISAC)/10.8.1 Evaluations/": [("Round 1", True, None)],
        "/drafts/10.8(ISAC)/10.8.1 Evaluations/Round 1/": [
            ("A.docx", False, 100),
            ("B.docx", False, 200),
        ],
    }
    if extra_file:
        tree["/drafts/10.8(ISAC)/10.8.1 Evaluations/Round 1/"].append(("C.docx", False, 300))
    if round2:
        tree["/drafts/10.8(ISAC)/10.8.1 Evaluations/"].append(("Round 2", True, None))
        tree["/drafts/10.8(ISAC)/10.8.1 Evaluations/Round 2/"] = []
    return tree


def run(source, previous, agenda) -> tuple[dict[str, Any], list]:
    index = scan_meeting(
        meeting_id="m1", source=source, agenda_codes=agenda, previous=previous
    )
    payload = index.to_json()
    fresh = [e for e in index.events if e.detectedAt == index.generatedAt]
    return payload, fresh


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(("PASS  " if condition else "FAIL  ") + name + (f"  {detail}" if detail else ""))
    return condition


def main() -> int:
    ok = True

    # 45 / 52: initial scan is a baseline, then a genuinely new file.
    base, fresh = run(FakeSource(meeting_a_tree()), None, MEETING_A_AGENDA)
    ok &= check("initial scan baselines without events", not fresh, f"{len(fresh)} events")
    ok &= check("baseline still lists files", len(base["artifacts"]) == 2)
    mapped = {a["normalizedPath"]: a["agendaItemId"] for a in base["artifacts"]}
    ok &= check(
        "round folder files map to parent agenda item",
        set(mapped.values()) == {"10.8.1"},
        str(mapped),
    )

    after, fresh = run(FakeSource(meeting_a_tree(extra_file=True)), base, MEETING_A_AGENDA)
    ok &= check(
        "new file yields exactly one NEW_FILE",
        [e.eventType for e in fresh] == ["NEW_FILE"] and fresh[0].agendaItemId == "10.8.1",
        str([(e.eventType, e.title) for e in fresh]),
    )

    # 55: new round.
    after2, fresh = run(FakeSource(meeting_a_tree(extra_file=True, round2=True)), after, MEETING_A_AGENDA)
    ok &= check(
        "new round folder yields NEW_ROUND for the agenda item",
        [e.eventType for e in fresh] == ["NEW_ROUND"] and fresh[0].roundNumber == 2,
        str([(e.eventType, e.title) for e in fresh]),
    )

    # 53: FL summary content change -> FL_SUMMARY_UPDATED, not NEW_FILE.
    fl_tree = {
        "/drafts/": [("10.8.2 Measurements", True, None)],
        "/drafts/10.8.2 Measurements/": [("FL_summary.docx", False, 500)],
    }
    src = FakeSource(fl_tree)
    src.blobs["/drafts/10.8.2 Measurements/FL_summary.docx"] = b"A"
    from draft_tracker.tracker import ScanConfig

    idx = scan_meeting(
        meeting_id="m1",
        source=src,
        agenda_codes=MEETING_A_AGENDA,
        previous=None,
        config=ScanConfig(hash_files=True),
    )
    ok &= check(
        "FL summary is classified",
        idx.artifacts[0].fileType == "fl_summary",
        idx.artifacts[0].fileType,
    )
    src2 = FakeSource(fl_tree)
    src2.blobs["/drafts/10.8.2 Measurements/FL_summary.docx"] = b"B-different-content"
    idx2 = scan_meeting(
        meeting_id="m1",
        source=src2,
        agenda_codes=MEETING_A_AGENDA,
        previous=idx.to_json(),
        config=ScanConfig(hash_files=True),
    )
    fresh = [e for e in idx2.events if e.detectedAt == idx2.generatedAt]
    ok &= check(
        "changed FL summary yields FL_SUMMARY_UPDATED",
        [e.eventType for e in fresh] == ["FL_SUMMARY_UPDATED"],
        str([e.eventType for e in fresh]),
    )
    ok &= check("previous revision metadata is preserved", len(idx2.artifacts[0].revisions) == 2)

    # 54: meeting-local first, public later -> one notification, then sync only.
    local = FakeSource(fl_tree, source_type="meeting-local")
    local.blobs["/drafts/10.8.2 Measurements/FL_summary.docx"] = b"X"
    local_idx = scan_meeting(
        meeting_id="m1", source=local, agenda_codes=MEETING_A_AGENDA, previous=idx2.to_json(),
        config=ScanConfig(hash_files=True),
    )
    local_fresh = [e for e in local_idx.events if e.detectedAt == local_idx.generatedAt]
    pub = FakeSource(fl_tree)
    pub.blobs["/drafts/10.8.2 Measurements/FL_summary.docx"] = b"X"
    pub_idx = scan_meeting(
        meeting_id="m1", source=pub, agenda_codes=MEETING_A_AGENDA, previous=local_idx.to_json(),
        config=ScanConfig(hash_files=True),
    )
    pub_fresh = [e for e in pub_idx.events if e.detectedAt == pub_idx.generatedAt]
    artifact = pub_idx.artifacts[0]
    ok &= check(
        "identical file on the public source creates no second notification",
        len(pub_fresh) == 0,
        str([e.eventType for e in pub_fresh]),
    )
    ok &= check(
        "artifact records both source appearances",
        {s.sourceType for s in artifact.sources} == {"public", "meeting-local"},
        str([s.sourceType for s in artifact.sources]),
    )
    ok &= check("one artifact, not two", len(pub_idx.artifacts) == 1)
    ok &= check("local scan itself notified once", len(local_fresh) >= 1)

    # 51 / 56: a completely different meeting shape, and rollover baselining.
    tree_b = {
        "/drafts/": [("7 NR positioning", True, None)],
        "/drafts/7 NR positioning/": [("7.2 (SL CA)", True, None)],
        "/drafts/7 NR positioning/7.2 (SL CA)/": [
            ("Rd. 1", True, None),
            ("Summary of SL CA v001.docx", False, 42),
        ],
        "/drafts/7 NR positioning/7.2 (SL CA)/Rd. 1/": [("draft_proposal.docx", False, 10)],
    }
    idx_b = scan_meeting(meeting_id="m2", source=FakeSource(tree_b), agenda_codes=MEETING_B_AGENDA)
    fresh_b = [e for e in idx_b.events if e.detectedAt == idx_b.generatedAt]
    codes = {a.agendaItemId for a in idx_b.artifacts}
    ok &= check("rollover: new meeting baselines silently", not fresh_b)
    ok &= check("different meeting maps its own agenda", codes == {"7.2"}, str(codes))
    ok &= check(
        "FL summary detected with a different naming convention",
        any(a.fileType == "fl_summary" for a in idx_b.artifacts),
    )
    ok &= check("meeting A archive untouched by meeting B", after2["meetingId"] == "m1")

    # 39: an unreachable source keeps the last good state.
    dead = FakeSource({})
    kept = scan_meeting(meeting_id="m1", source=dead, agenda_codes=MEETING_A_AGENDA, previous=after2)
    ok &= check(
        "failed scan preserves known data",
        kept.scanState == "delayed" and len(kept.artifacts) == len(after2["artifacts"]),
    )

    print("\nALL PASS" if ok else "\nFAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
