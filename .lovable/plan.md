# Schedule gaps are always an error, fix Wednesday's Tamna BC gaps, and make "Verify data" fail only on real problems

## What is checked (live GitHub data, 15:30 UTC)
- The timetable now uses **Hiroki v05** and Chair notes v05 (rebuilt 12:39 UTC).
- Wednesday Room 201: Sensing is no longer 09:30–09:36. The "(6)" typo no longer adds up, so the block shows Hiroki's full 09:00–10:30 slot (Waveform + Sensing) with the note "Minutes don't add up: items total 36 min, block is 90 min."
- **Wednesday 14 Oct, Tamna BC Hall, 17:00–19:30 (your screenshot).** The official v00 cell says `6GR (150) | 10.4.1 (40) | 10.4.2 (40) | 10.5.5 (40) | 10.5.3.1 (30)`, which adds up to 150 minutes exactly. The published timetable has:
  - 10.4.1 17:00–17:40 (correct)
  - **10.4.2 17:40–18:20 missing**
  - **10.5.5 18:20–19:00 missing**
  - "Modulation 10.3.2 18:00–18:30", which is not in the Tamna cell at all. It is the Yeongju A Hall item ("Channel coding (60) | Modulation (30)")
  - 10.5.3.1 19:00–19:30 (correct)
  So a block from another room landed in Tamna BC, and resolving the overlap removed both real items around it. The exact step where Modulation gets the wrong room is **not confirmed yet**. Step 1 finds it.
- "Verify data" fails for one reason only: **no remote meeting server address has been entered**. Everything else passed. That is a missing optional source, not broken data.
- The timetable updater ran at 03:32, then not again until 11:44, even though it is scheduled every 5 minutes. GitHub skips scheduled runs when it is busy.
- GitHub also warns that `actions/checkout@v4` and `actions/setup-python@v5` use the old Node 20. This is only a warning for now, but they should be updated.

## Steps
1. **Find why Modulation lands in Tamna BC.** Trace the Wednesday 17:00 cells from all three files (official v00, Sorour v00, Hiroki v05) through room matching and the merge. Check whether a cell spanning two columns, or a copy of the grid in Hiroki's or Sorour's file, is put in the wrong room.
2. **Fix that,** so each item stays in the room whose column it was written in. The 17:00–19:30 block then reads 10.4.1 → 10.4.2 → 10.5.5 → 10.5.3.1 with no gap.
3. **Gaps are always an error.** After every rebuild, each source block (a cell with a stated time range) is checked against the published timetable for that room. If any part of that time range has no session, the rebuild **fails**, and the previous schedule stays online. The error names the room, day and missing minutes, and appears on the Ingestion status page and in "Verify data". The only allowed exception is a time range the file itself leaves empty.
4. Regression tests: one for this Wednesday Tamna cell (four items, no gap, no Modulation), and one for the gap check itself.
5. **Missing remote address = note, not failure.** The job only fails on real problems: stale data, a Draft-only timetable, a schedule gap, a server address that was entered but doesn't answer, or a missing login.
6. **Catch silent refresh gaps.** During meeting-week session hours, data older than 2 hours fails the check (6 hours otherwise). When the timetable is stale, "Verify data" starts "Update schedule" and "Track drafts" itself.
7. **Short blocks.** Any block under 10 minutes shows as a note on the Ingestion status page.
8. Update GitHub Actions to `actions/checkout@v5` and `actions/setup-python@v6` in all workflows, which removes the Node 20 warning.
9. Rebuild RAN1#126bis only. Check Wednesday room by room against the official v00 and Hiroki v05, run the check locally, then trigger "Verify data" once and confirm it is green.

## Technical details
- Room assignment / merge: `ingestion/block_schedule.py` (`room_for`, column spans, `own_table` ranking), `ingestion/canonical_schedule.py` (overlap resolution and `_score_room_affinity`), `ingestion/room_resolver.py`.
- Gap check: new rule in `ingestion/validator.py`. Coverage per (date, room) for every parsed source session with explicit times, compared with canonical sessions; validation errors keep the previous schedule. The result is also written to the health record as a `warn`.
- `ingestion/health.py`: `skipped-no-host` becomes `info`; short-block note; schedule-gap warn.
- `scripts/check-meeting-health.mjs`: freshness limit of 2 h when active and 05–19 UTC on weekdays, otherwise 6 h.
- `.github/workflows/verify-data.yml`: `permissions: actions: write`; `gh workflow run update-schedule.yml` / `update-drafts.yml` when stale.
- Record in roadmap.md; also activate the remaining skill drafts (drafts-live-merge-check, new-meeting-setup, publish-and-verify).
