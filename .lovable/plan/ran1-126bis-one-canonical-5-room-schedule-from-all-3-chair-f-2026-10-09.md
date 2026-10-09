# RAN1#126bis: one canonical 5-room schedule from all 3 chair files

## What's wrong today
- The current schedule is built only from `Draft RAN1#126b online and offline schedules - v03.docx`. Sorour's v00 and Hiroki's v01 files are not in the source list at all, so their room names and detailed splits are missing.
- Tuesday Online Session 3 (10.5.4.1–.4): the four stated durations (50+25+40+35 = 150 min) are squeezed into the 120-min slot by cutting off the last item, so 10.5.4.4 gets 5 min and 10.5.4.2 shows no time.

## Core model: one colour = one room
- Every cell colour in the schedule tables is one room (one column in the app).
- Whether a room is online or offline comes from the table it appears in: tables with "offline" in the heading are offline, the others online.
- The number of rooms is simply the number of distinct colours found — this meeting 5 (3 online, 2 offline); it can be different next meeting.
- The room's name comes from any file that names it — mainly the colour-coded room legend in the top-right corner of each table (the name is written in the same colour as its column), plus "Room:" lines and headings — e.g. "Yeongju B, 1F (RAN1 Brk2)". The online room whose column says "Main session / RAN1 #N commences" is RAN1 Main.

```text
This meeting (example, not hard-coded):
Online  colour A (white)  = RAN1 Main
Online  colour B (grey)   = breakout room, name from whichever file gives it
Online  colour C (orange) = breakout room, e.g. Yeongju B, 1F
Offline colour D          = offline room 1
Offline colour E          = offline room 2
```

## Core principle: overlay every table
Every online and offline table from every schedule file is laid on top of the others, matched by day, time and room (= colour). For each slot the result keeps:
- the most granular version that has real times (a detailed split beats a broad block);
- items that appear in only one file (union — nothing dropped);
- one copy of identical blocks, with every file that contained it noted;
- disagreements shown and flagged, never silently picked;
- the latest revision of each file wins over its older versions.
All changes below follow this rule.

## Changes
1. **Pick up all three files automatically**
   - Make discovery find `RAN1#126b Sorour sessions online and offline schedules - v00.docx` and `RAN1#126bis schedule for Hiroki Adhoc2 sessions_v01.docx` (both "126b" and "126bis" spellings count as this meeting; plain "RAN1#126" still does not).
   - Search every subfolder (any depth) of the meeting's own `Inbox` (e.g. `/ftp/tsg_ran/WG1_RL1/TSGR1_126b/Inbox/`), and during meeting week also `/ftp/Meetings_3GPP_SYNC/RAN1/Inbox`. Works the same for every meeting. The 10.10.10.10 venue server stays as existing plumbing (still off).
   - First check why the existing scan missed these two files (wrong folder depth, name pattern, or the data simply not rebuilt since they were uploaded) and fix that cause.
   - Always take the latest version of each of the three families; show all three filenames in "Schedule based on".
2. **Rooms from colours**: build one room per distinct colour across all files' tables, online or offline per the table heading. No fixed "Offline Session 1/2" by position anymore — offline rooms are matched by colour across all files, exactly like online rooms.
3. **Room names from any file**: read "Room:" lines and headings in all files and attach each name to the room with the matching colour. Never create a column for a name alone (fixes today's stray "203" and "Yeongju B (1F)" columns).
4. **Detailed schedules overlay**: "Detailed Schedule for ..." sections in any file replace the broad block in the same colour/room and time with their agenda-level blocks and times — for online and offline alike.
5. **No made-up times, anywhere.** A block is split only when the files give usable times/minutes that fit inside the block.
   - Otherwise it stays one big block listing all its agenda items without times (e.g. Monday "10.5.4.x" 14:30–16:00 lists 10.5.4.1, .3, .4; Tuesday 10.5.4 08:30–10:30 lists .1–.4 with the chair's stated minutes shown as text, since 150 min doesn't fit 120).
   - When minutes don't add up, the block lists each item with its stated minutes (e.g. "10.5.4.1 · 50 min"), and tapping it shows: "Minutes don't add up: items total 150 min, block is 120 min."
   - Removes today's 5-minute placeholders (Monday 10.5.4.1 16:00–16:05 etc., 9.3.1, 10.8.2) and anything placed after a parent ends or inside a coffee/lunch break.
   - If you follow any of those agenda items, the whole block appears in My agenda, filters, NOW and calendar export.
   - When a newer schedule version provides a real split, the split replaces the big block automatically.
6. **Readable short blocks**: minimum card height so every block shows code and time.
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
- Overlay check: for every day and slot, compare all three files' tables side by side against the app's result, and confirm the app shows the most detailed timed version, nothing from any file is missing, no duplicates, and conflicts are flagged. Report any slot that differs.
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
