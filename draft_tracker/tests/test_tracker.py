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
    ids=set(index.newEventIds); fresh = [e for e in index.events if e.id in ids]
    return payload, fresh


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(("PASS  " if condition else "FAIL  ") + name + (f"  {detail}" if detail else ""))
    return condition


def dynamic_structure_tests() -> bool:
    """The directory tree is the source of truth: no template is ever assumed."""
    ok = True
    agenda = {"10.8": "ISAC", "10.8.1": "Evaluations", "10.8.2": "Measurements", "10.8.3": "Deployment"}

    # 30: no round folder anywhere; an FL summary simply appears.
    flat_before = {
        "/drafts/": [("10.8.1", True, None)],
        "/drafts/10.8.1/": [("A.docx", False, 1), ("B.docx", False, 2)],
    }
    flat_after = {
        "/drafts/": [("10.8.1", True, None)],
        "/drafts/10.8.1/": [
            ("A.docx", False, 1),
            ("B.docx", False, 2),
            ("FL_summary.docx", False, 3),
        ],
    }
    base, _ = run(FakeSource(flat_before), None, agenda)
    _, fresh = run(FakeSource(flat_after), base, agenda)
    ok &= check(
        "structure without rounds: single NEW_FILE, no round invented",
        [e.eventType for e in fresh] == ["NEW_FILE"]
        and fresh[0].semanticType == "FL_SUMMARY_UPDATED"
        and all(e.roundNumber is None for e in fresh),
        str([(e.eventType, e.semanticType) for e in fresh]),
    )

    # 31: an arbitrary new folder is discovered without any configuration.
    arb_before = {"/drafts/": [("10.8.1", True, None)], "/drafts/10.8.1/": [("A.docx", False, 1)]}
    arb_after = {
        "/drafts/": [("10.8.1", True, None)],
        "/drafts/10.8.1/": [("A.docx", False, 1), ("Agreement discussion", True, None)],
        "/drafts/10.8.1/Agreement discussion/": [("B.docx", False, 2)],
    }
    base, _ = run(FakeSource(arb_before), None, agenda)
    idx_arb, fresh = run(FakeSource(arb_after), base, agenda)
    types = sorted(e.eventType for e in fresh)
    ok &= check(
        "arbitrary folder: NEW_FOLDER + NEW_FILE, never NEW_ROUND",
        types == ["NEW_FILE", "NEW_FOLDER"]
        and all(e.semanticType != "NEW_ROUND" for e in fresh),
        str([(e.eventType, e.semanticType, e.title) for e in fresh]),
    )
    ok &= check(
        "unclassified folder stays generic",
        any(
            f["name"] == "Agreement discussion" and f["folderType"] == "generic"
            for f in idx_arb["folders"]
        ),
    )
    group_keys = {e.groupKey for e in fresh}
    ok &= check(
        "files inside a brand-new folder share one notification group",
        len(group_keys) == 1 and None not in group_keys,
        str(group_keys),
    )

    # 32: a file four levels below the agenda folder still maps to it.
    deep = {
        "/drafts/": [("10.8.1", True, None)],
        "/drafts/10.8.1/": [("A", True, None)],
        "/drafts/10.8.1/A/": [("B", True, None)],
        "/drafts/10.8.1/A/B/": [("C", True, None)],
        "/drafts/10.8.1/A/B/C/": [("FL_summary.docx", False, 9)],
    }
    idx_deep, _ = run(FakeSource(deep), None, agenda)
    art = idx_deep["artifacts"][0]
    ok &= check(
        "deeply nested file maps to the nearest agenda ancestor",
        art["agendaItemId"] == "10.8.1" and art["fileType"] == "fl_summary",
        f"{art['agendaItemId']} {art['normalizedPath']}",
    )

    # 33: three agenda items with three different structures at once.
    mixed = {
        "/drafts/": [("10.8.1", True, None), ("10.8.2", True, None), ("10.8.3", True, None)],
        "/drafts/10.8.1/": [("Round 1", True, None)],
        "/drafts/10.8.1/Round 1/": [("A.docx", False, 1)],
        "/drafts/10.8.2/": [("B.docx", False, 2), ("FL.docx", False, 3)],
        "/drafts/10.8.3/": [("Agreement", True, None)],
        "/drafts/10.8.3/Agreement/": [("C.docx", False, 4)],
    }
    idx_mixed, _ = run(FakeSource(mixed), None, agenda)
    per_code = {}
    for a in idx_mixed["artifacts"]:
        per_code.setdefault(a["agendaItemId"], []).append(a["filename"])
    ok &= check(
        "different structures coexist in one meeting",
        sorted(per_code) == ["10.8.1", "10.8.2", "10.8.3"],
        str(per_code),
    )
    ftypes = {f["name"]: f["folderType"] for f in idx_mixed["folders"]}
    ok &= check(
        "only genuine round folders are labelled rounds",
        ftypes.get("Round 1") == "round" and ftypes.get("Agreement") == "generic",
        str(ftypes),
    )

    # 10: an unmappable file is kept, never guessed onto an agenda item.
    orphan = {
        "/drafts/": [("Logistics", True, None)],
        "/drafts/Logistics/": [("bus_times.docx", False, 5)],
    }
    idx_orphan, _ = run(FakeSource(orphan), None, agenda)
    orphan_art = idx_orphan["artifacts"][0]
    ok &= check(
        "unmapped file preserved with agendaItemId=null",
        orphan_art["agendaItemId"] is None
        and orphan_art["normalizedPath"] == "logistics/bus_times.docx",
        str(orphan_art["agendaItemId"]),
    )

    # 20 / 6F: structure appearing mid-week needs no code change.
    grow_a = {"/drafts/": [("10.8.1", True, None)], "/drafts/10.8.1/": [("fileA.docx", False, 1)]}
    grow_b = dict(grow_a)
    grow_b["/drafts/10.8.1/"] = [("fileA.docx", False, 1), ("Revised proposals", True, None)]
    grow_b["/drafts/10.8.1/Revised proposals/"] = [("fileB.docx", False, 2)]
    base, _ = run(FakeSource(grow_a), None, agenda)
    idx_grow, fresh = run(FakeSource(grow_b), base, agenda)
    ok &= check(
        "folder created during the meeting is discovered automatically",
        any(e.eventType == "NEW_FOLDER" and "Revised proposals" in e.title for e in fresh),
    )

    # 21: a vanished folder is reported as removed, never as a rename.
    idx_gone, fresh = run(FakeSource(grow_a), idx_grow, agenda)
    ok &= check(
        "removed folder yields FOLDER_REMOVED and FILE_REMOVED",
        sorted({e.eventType for e in fresh}) == ["FILE_REMOVED", "FOLDER_REMOVED"],
        str([(e.eventType, e.title) for e in fresh]),
    )

    # 5: same filename repeated per round stays two artifacts, latest resolvable.
    dup = {
        "/drafts/": [("10.8.1", True, None)],
        "/drafts/10.8.1/": [("Round 1", True, None), ("Round 2", True, None)],
        "/drafts/10.8.1/Round 1/": [("FL_summary_v01.docx", False, 10)],
        "/drafts/10.8.1/Round 2/": [("FL_summary_v01.docx", False, 11)],
    }
    idx_dup, _ = run(FakeSource(dup), None, agenda)
    ok &= check(
        "same filename in two rounds stays two distinct artifacts",
        len(idx_dup["artifacts"]) == 2
        and len({a["id"] for a in idx_dup["artifacts"]}) == 2,
        str([a["normalizedPath"] for a in idx_dup["artifacts"]]),
    )
    return ok


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
        "new round folder yields NEW_FOLDER labelled NEW_ROUND",
        [e.eventType for e in fresh] == ["NEW_FOLDER"]
        and fresh[0].semanticType == "NEW_ROUND"
        and fresh[0].roundNumber == 2,
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
    fresh = [e for e in idx2.events if e.id in set(idx2.newEventIds)]
    ok &= check(
        "changed FL summary yields FILE_UPDATED labelled FL_SUMMARY_UPDATED",
        [e.eventType for e in fresh] == ["FILE_UPDATED"]
        and fresh[0].semanticType == "FL_SUMMARY_UPDATED",
        str([(e.eventType, e.semanticType) for e in fresh]),
    )
    ok &= check("previous revision metadata is preserved", len(idx2.artifacts[0].revisions) == 2)

    # 54: meeting-local first, public later -> one notification, then sync only.
    local = FakeSource(fl_tree, source_type="meeting-local")
    local.blobs["/drafts/10.8.2 Measurements/FL_summary.docx"] = b"X"
    local_idx = scan_meeting(
        meeting_id="m1", source=local, agenda_codes=MEETING_A_AGENDA, previous=idx2.to_json(),
        config=ScanConfig(hash_files=True),
    )
    local_fresh = [e for e in local_idx.events if e.id in set(local_idx.newEventIds)]
    pub = FakeSource(fl_tree)
    pub.blobs["/drafts/10.8.2 Measurements/FL_summary.docx"] = b"X"
    pub_idx = scan_meeting(
        meeting_id="m1", source=pub, agenda_codes=MEETING_A_AGENDA, previous=local_idx.to_json(),
        config=ScanConfig(hash_files=True),
    )
    pub_fresh = [e for e in pub_idx.events if e.id in set(pub_idx.newEventIds)]
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
    fresh_b = [e for e in idx_b.events if e.id in set(idx_b.newEventIds)]
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

    ok &= dynamic_structure_tests()

    print("\nALL PASS" if ok else "\nFAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
