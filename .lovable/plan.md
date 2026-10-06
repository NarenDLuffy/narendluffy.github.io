# Fix missing Friday Offline Session 2

## What is wrong
The latest RAN1#126bis schedule document has two Friday afternoon offline cells: "To be assigned by Sorour" (Offline 1) and "To be assigned by Hiroki" (Offline 2), covering 14:30–16:30 and 17:00–19:30.
The app currently shows only one Friday offline session: Offline Session 1, 14:30–16:30. Offline 2 is missing entirely, and neither lane has the 17:00–19:30 block.

## Likely causes (to confirm first)
1. The Hiroki cell has no fill colour of its own in Word, so it is matched to the wrong chair lane or dropped as a placeholder.
2. The Friday afternoon cells span both afternoon rows (vertically merged). The parser reads only the first row and skips the merged continuation, so 17:00–19:30 is lost.
3. The canonical merge may treat two "To be assigned" placeholders at the same time as duplicates and keep only one.

## Fix
- Give unfilled cells the fill colour of their column (the same column on other days), so Hiroki's cell stays in the Offline 2 lane.
- Expand vertically merged cells so each time block they cover gets its own session.
- Never merge placeholder sessions that belong to different chair lanes.
- Keep "To be assigned by <chair>" as a visible placeholder block in that chair's column.

## Verify
- Re-parse the current document: Friday must show Offline 1 and Offline 2 at both 14:30–16:30 and 17:00–19:30, and the other days must stay the same.
- Rebuild the published schedule data so the live app updates without republishing.
- Check the Friday timetable in the browser.

## Technical details
- `ingestion/block_schedule.py`: lane-fill inference for unfilled and placeholder cells; handle `vMerge` continuation rows in `_row_cells` / the block loop.
- `ingestion/canonical_schedule.py`: dedupe key includes `chairLaneId`.
- Regenerate `public/data/meetings/ran1-126-bis/*.json` with `ingestion/generate_schedule.py`.
