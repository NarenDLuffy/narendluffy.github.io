# Fix RAN1#126bis schedule: use only the latest official files

## What is wrong today (checked in the published data)
- The schedule was last rebuilt at 23:52 UTC yesterday from **both** the old "Draft RAN1#126b online and offline schedules - v03" and the new official "RAN1#126b online and offline schedules - v00", plus Sorour v00 and Hiroki v01. The draft and the official version are mixed together.
- Monday 11:00–12:30: only Tamna BC Hall, Room 201 and Room 203 have sessions. **Yeongju A Hall and Yeongju B Hall are empty**, but they have sessions the rest of the day.
- Several Monday morning blocks are marked as "inferred duration", which means the times may have been guessed from the mixed files.
- The exact reason the Yeongju sessions are missing is **not confirmed yet**. The most likely cause is the old draft overlapping the official file, so the official sessions for those rooms get lost. Step 1 checks this before anything is changed.

## Steps
1. **Find the cause.** Download the four current files. List the Monday 11:00–12:30 rows for the Yeongju rooms in each file. Then follow those rows through the merge to see where they get dropped.
2. **Official schedule priority, for every meeting.** Once a file without "Draft" in its name exists for a schedule series, ignore the "Draft …" files of that series, whatever their version numbers. Within the files that count, keep using only the latest version of each (Sorour v00, Hiroki v01, official v00). Chair notes follow the same rule.
3. **Fix the cause found in step 1.** For example, the Yeongju lanes might be lost when the online and offline tables are matched up, or they might get lost in the merge. Add a check that fails if Monday 11:00–12:30 has no Yeongju sessions while the source files list them.
4. **Rebuild only RAN1#126bis and publish it**, using the rebuild option for a single meeting. Then compare Monday with the official v00 file in the preview, room by room.
5. On the Schedule page, the list of source files will no longer show the draft v03.

## Technical details
- `ingestion/schedule_discovery.py` / `live.py`: group files into a series by their name with the "Draft" prefix and the version removed. Keep the latest revision, and leave out drafts when an official file exists. Record this rule in AGENTS.md.
- `canonical_schedule.py` / `block_schedule.py`: investigate why blocks for online lanes D9D9D9/FFD966 are missing from 11:00 to 12:30. Add a regression test in `ingestion/tests`.
- Validator: a meeting's rebuild fails if a source table's lane/slot doesn't appear in the canonical output.

## After this plan (one at a time, as agreed)
- **Drafts source cleanup**: during the meeting week, stop showing old files from the per-meeting archive (e.g. 10.8.1 Round 1).
- **Small leftover from leaf agendas**: drafts filed under a branch (e.g. 10.7) don't yet appear under a followed leaf (10.7.1) in "Draft activity for my items".
