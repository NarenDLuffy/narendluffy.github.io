# RAN1#126bis: one canonical 5-room schedule from all 3 chair files

## What's wrong today
- The current schedule is built only from `Draft RAN1#126b online and offline schedules - v03.docx`. Sorour's v00 and Hiroki's v01 files are not in the source list at all, so their room names and detailed splits are missing.
- Tuesday Online Session 3 (10.5.4.1–.4): the four stated durations (50+25+40+35 = 150 min) are squeezed into the 120-min slot by cutting off the last item, so 10.5.4.4 gets 5 min and 10.5.4.2 shows no time.

## Target: exactly 5 rooms
```text
Online  - White  = RAN1 Main          (main grid)
Online  - Grey   = Sorour online room (name from Sorour's file)
Online  - Orange = Hiroki online room (e.g. "RAN1_Brk#2, Yeongju B, 1F" from Hiroki's file)
Offline - Offline Session 1           (same room across all 3 files)
Offline - Offline Session 2           (same room across all 3 files)
```

## Changes
1. **Pick up all three files automatically**
   - Make discovery find `RAN1#126b Sorour sessions online and offline schedules - v00.docx` and `RAN1#126bis schedule for Hiroki Adhoc2 sessions_v01.docx` (both "126b" and "126bis" spellings count as this meeting; plain "RAN1#126" still does not).
   - Search every subfolder (any depth) of the meeting's own `Inbox` (e.g. `/ftp/tsg_ran/WG1_RL1/TSGR1_126b/Inbox/`), and during meeting week also `/ftp/Meetings_3GPP_SYNC/RAN1/Inbox`. Works the same for every meeting. The 10.10.10.10 venue server stays as existing plumbing (still off).
   - First check why the existing scan missed these two files (wrong folder depth, name pattern, or the data simply not rebuilt since they were uploaded) and fix that cause.
   - Always take the latest version of each of the three families; show all three filenames in "Schedule based on".
2. **Main file = the skeleton**: times, days, and the white / grey / orange online columns plus the two offline columns.
3. **Room names from the chair files**
   - Read "Room:" lines in all three files (main, Hiroki, Sorour — any of them may have them) and attach each to the matching coloured online column (Hiroki = orange, Sorour = grey), shown as e.g. "Yeongju B, 1F (RAN1 Brk2)".
   - Offline room names found in any file are applied to Offline Session 1/2.
   - Never create extra columns: everything maps into the 5 rooms above.
4. **Detailed schedule from the chair files**
   - Find the "Detailed Schedule for ..." sections in Hiroki's and Sorour's files and replace the broad main-grid blocks in their column with the detailed agenda-level blocks and times.
   - Offline blocks: combine all 3 files into one canonical set per offline room; duplicates merged, disagreements flagged.
5. **Fix overfull splits** (Tuesday 10.5.4): if stated minutes exceed the slot and no detailed file gives exact times, scale them to fit the slot (none dropped) and show the stated minutes on the card. If a detailed file gives exact times, use those.
6. **Readable short blocks**: minimum card height so every split block shows code and time.
7. **No made-up 5-minute slots** (Monday room "203": 10.5.4.1 16:00–16:05, .3 16:05–16:10, .4 16:10–16:15, while the parent 10.5.4.x runs 14:30–16:00; similar 5-min 9.3.1 and 10.8.2 in RAN1 Main):
   - Sub-items without stated minutes are currently given a 5-minute placeholder and placed after the parent ends. Instead, keep them inside the parent block: listed as the block's agenda items (one block, no invented times), or split evenly only if the file states order but no minutes — never past the parent's end or into a break.
   - Nothing is ever scheduled inside a coffee/lunch break.
8. **No duplicate blocks**: the same block currently appears twice (e.g. Offline Session 1 14:55–15:40, RAN1 Main 15:30–16:30). Identical blocks from different files are merged into one.
9. **No stray rooms**: "203" and "Yeongju B (1F)" currently appear as extra columns next to "Online Session 3". Room names must attach to their existing column (by colour/content), not create a new one.

## Works for any chairs, any meeting (no names in the code)
- Hiroki, Sorour and 126bis above are only this week's example. The code never looks for a person's name.
- Each schedule file is recognised by what's inside: it has online/offline tables, cell colours, "Detailed Schedule for", "Room:" lines. Any number of such files (usually 3) are all used.
- Which online column a file belongs to is worked out from the tables: the colour of its cells and which agenda items/times it shares with a coloured column in the main grid — not from its filename.
- Lanes come from the data: one column per online colour, plus the offline sessions. If a future meeting has 4 colours, it gets 4 online columns automatically.
- A health check on each rebuild flags "needs review" in the app when a schedule-looking file was found but couldn't be matched to a column, so problems show up instead of silently disappearing.
- Tests use saved copies of this meeting's three files.

## Verify
- Rebuild RAN1#126bis: as many rooms as the files define (no fixed number; 5 this meeting); sources list shows v03, Sorour v00, Hiroki v01.
- Orange column shows Hiroki's room name; grey shows Sorour's.
- Tuesday Online Session 3 shows all four 10.5.4.x blocks with times.
- Tests for: 126b/126bis name matching, room-name extraction, detailed-section override, 5-room cap, overfull scaling.

## Technical details
- `ingestion/live.py` / `schedule_discovery.py`: meeting-name matching and family/latest-revision selection for chair files.
- `ingestion/docx_schedule.py`: parse "Room:" and "Detailed Schedule for" sections; tag chair source with lane colour (from main grid lane owner).
- `ingestion/canonical_schedule.py`: map chair-file blocks onto the colour lane / offline lane; no new rooms; offline union.
- `ingestion/block_schedule.py`: proportional fit for overfull child splits.
- `src/components/Timetable.tsx`: min card height.
- AGENTS: record "lanes and chair-file ownership are inferred from table colours/content, never from names".
