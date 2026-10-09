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
   - Always take the latest version of each of the three families; show all three filenames in "Schedule based on".
2. **Main file = the skeleton**: times, days, and the white / grey / orange online columns plus the two offline columns.
3. **Room names from the chair files**
   - Read "Room:" lines in Hiroki's and Sorour's files and attach them to the matching coloured online column (Hiroki = orange, Sorour = grey), shown as e.g. "Yeongju B, 1F (RAN1 Brk2)".
   - Offline room names found in any file are applied to Offline Session 1/2.
   - Never create extra columns: everything maps into the 5 rooms above.
4. **Detailed schedule from the chair files**
   - Find the "Detailed Schedule for ..." sections in Hiroki's and Sorour's files and replace the broad main-grid blocks in their column with the detailed agenda-level blocks and times.
   - Offline blocks: combine all 3 files into one canonical set per offline room; duplicates merged, disagreements flagged.
5. **Fix overfull splits** (Tuesday 10.5.4): if stated minutes exceed the slot and no detailed file gives exact times, scale them to fit the slot (none dropped) and show the stated minutes on the card. If a detailed file gives exact times, use those.
6. **Readable short blocks**: minimum card height so every split block shows code and time.

## Verify
- Rebuild RAN1#126bis: exactly 5 rooms; sources list shows v03, Sorour v00, Hiroki v01.
- Orange column shows Hiroki's room name; grey shows Sorour's.
- Tuesday Online Session 3 shows all four 10.5.4.x blocks with times.
- Tests for: 126b/126bis name matching, room-name extraction, detailed-section override, 5-room cap, overfull scaling.

## Technical details
- `ingestion/live.py` / `schedule_discovery.py`: meeting-name matching and family/latest-revision selection for chair files.
- `ingestion/docx_schedule.py`: parse "Room:" and "Detailed Schedule for" sections; tag chair source with lane colour (from main grid lane owner).
- `ingestion/canonical_schedule.py`: map chair-file blocks onto the colour lane / offline lane; no new rooms; offline union.
- `ingestion/block_schedule.py`: proportional fit for overfull child splits.
- `src/components/Timetable.tsx`: min card height.
- Memory/AGENTS: record "5 canonical rooms: main grid defines lanes, chair files supply room names and detail".
