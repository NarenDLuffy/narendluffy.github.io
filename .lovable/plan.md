# Fix Tuesday Online Session 3 split (10.5.4.1–.4)

## What's wrong
The v03 document gives 10.5.4.1 (50), .2 (25), .3 (40), .4 (35) = 150 min, but the slot is only 120 min (08:30–10:30). The app currently fills the slot in order and then cuts off, so:
- 10.5.4.1 08:30–09:20, .2 09:20–09:45, .3 09:45–10:25
- 10.5.4.4 gets only 10:25–10:30 (5 min) — practically invisible
- 10.5.4.2 (25 min) is too short on screen to show its time

## Fix
1. **Fit the children to the real slot proportionally** when the stated minutes exceed (or fall short of) the slot, instead of cutting off the last item. For Tuesday:
   - 10.5.4.1 08:30–09:10 (stated 50)
   - 10.5.4.2 09:10–09:30 (stated 25)
   - 10.5.4.3 09:30–10:02 (stated 40)
   - 10.5.4.4 10:02–10:30 (stated 35)
   Times rounded to whole minutes, last item always ends at the slot end.
2. **Show the chair's stated minutes** on each card and in the detail sheet (e.g. "stated 50 min"), plus a small note "Durations in the schedule exceed the slot — times scaled", so nothing is hidden.
3. **Readable short blocks**: give timetable cards a minimum height so every split block shows its code and time.
4. When stated minutes fit within the slot, behaviour is unchanged (exact times).

## Verify
- Parser test: 120-min slot with 50/25/40/35 children gives four blocks covering 08:30–10:30, none dropped.
- Rebuild RAN1#126bis and check Tuesday Online Session 3 shows all four blocks with times in the preview.

## Technical details
- `ingestion/block_schedule.py`: replace clip-at-end with proportional scaling in the child slot allocation; keep `minutes` (stated) on `AgendaSlot`, add scaled start/end.
- `src/components/Timetable.tsx` / `SessionCard.tsx`: min card height; render stated minutes + scaled note.
- Update `ingestion/tests/test_block_schedule_parsing.py`.
