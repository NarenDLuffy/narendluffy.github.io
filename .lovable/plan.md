# Offline sessions: two plain columns, and fix missing Friday Offline 2

## What changes
- **Online:** stays as it is. Each colour is one chair's column, and RAN1 Main is found from "Main session" or "RAN1 #number commences".
- **Offline:** stop using colour. The offline table becomes exactly two columns, Offline Session 1 and Offline Session 2, based on where each cell sits within its day (first half or second half).
- This also fixes Friday. The document has "To be assigned by Sorour" (Offline 1) and "To be assigned by Hiroki" (Offline 2) at 14:30–16:30 and 17:00–19:30. Right now the app shows only the Sorour block from 14:30 to 16:30.

## Fix
- In the offline table, choose each session's column by its position within the day, never by fill colour.
- Expand cells that span both afternoon rows so 17:00–19:30 shows up as well.
- Never merge sessions from different offline columns, including "To be assigned" placeholders.
- Update the project rules so the colour-per-chair rule applies to online sessions only.

## Verify
- Re-parse the current document. Every day must have Offline 1 and Offline 2 where the document has them, including both Friday afternoon blocks.
- Online columns must be unchanged: RAN1 Main plus the coloured vice-chair columns.
- Rebuild the published data so the live app updates, then check Friday in the browser.

## Technical details
- `ingestion/block_schedule.py`: for `mode == "offline"`, lane = index of the sub-column within the day span; no `chairLaneId` from fill. Handle `vMerge` continuation rows.
- `ingestion/live.py` `_name_tracks` / `ingestion/canonical_schedule.py`: offline rooms are keyed by lane index; dedupe includes the room.
- `AGENTS.md`: restrict the colour-lane rule to online tables. Add a task to `roadmap.md`.
- Regenerate `public/data/meetings/ran1-126-bis/*.json`.
