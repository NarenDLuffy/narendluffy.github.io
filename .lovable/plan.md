# Fix RAN1#126bis schedule: pick up Hiroki v05 and the 6-minute Sensing block

## What is checked so far (live published data, rebuilt 03:48 UTC today)
- The timetable is built from: official v00, Sorour v00, **Hiroki Adhoc2 v03**, Chair notes v03. Hiroki v05 is not among them.
- Wednesday 14 Oct, Room 201: "Sensing (10.8.x)" is published as **09:30–09:36**, marked "inferred duration". The next Room 201 block starts at 11:00, so the time after 09:36 is lost.
- Almost every Wednesday-morning block is "inferred duration", i.e. its length came from minutes written next to items, not from a stated end time.
- Why v05 is skipped is **not confirmed yet**. It could be: the file is in a folder or under a name the search doesn't reach, its name doesn't name the meeting the way the meeting filter expects, or it lands in a different "series" than v03, so v03 is not seen as older.
- Why Sensing gets 6 minutes is **not confirmed yet**. Most likely a number next to "10.8.x" in the cell (a count or a note, not minutes) is read as "6 min".

## Steps
1. **Find v05.** List every Hiroki file in the meeting folder and the sync mirror, and see which check drops v05 (search, meeting filter, or version grouping).
2. **Fix that check** so the newest Hiroki revision always wins, for every chair file, not just Hiroki's. Add a test with v03 and v05 names side by side.
3. **Find the 6.** Open Hiroki's Wednesday table (v05, and v03 for comparison) and look at the exact text of the Room 201 09:30 cell.
4. **Fix the reading of minutes.** A number counts as minutes only when it is clearly written as time (e.g. "30 min", "(30')") and the minutes fit inside the block. If they don't fit, the block keeps the full time slot and lists its items — times are never made up. Add a test for this cell.
5. **Rebuild RAN1#126bis only** and check Wednesday 14 Oct room by room against Hiroki v05 and the official v00: Sensing must run until the next block, and the source list must show Hiroki v05.
6. Add a health warning when a schedule block is shorter than 10 minutes, so this shows up on the Ingestion status page next time.

## Technical details
- Discovery/series: `ingestion/live.py` (`discover_sources`, `_belongs_to_meeting`, `_revision_family`, `_latest_revisions`) and `ingestion/schedule_discovery.py`.
- Minutes parsing / splitting: `ingestion/block_schedule.py` and `ingestion/canonical_schedule.py` (`inferred-duration` path around line 187). Fall back to the parent slot when stated minutes don't fit (existing rule in project knowledge).
- Tests in `ingestion/tests`; rebuild with `python -m ingestion.generate_schedule --meeting 126-bis`; health warning in `ingestion/health.py`.
- Also record this task in roadmap.md, and finish activating the three remaining meeting-week skills.
