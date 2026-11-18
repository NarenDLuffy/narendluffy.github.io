# Fix missing "NTN-NR" session (Room cell: R20 (60) / NTN-NR (40) / .9.5 NTN (20) | 6GR (90) / .10.7.1 / .10.3.1)

## What is wrong today (checked)
The schedule shows one "R20" block 14:00-15:00 with a warning ("9.5 (20) · 6GR (90)"), and labels the 6GR items as "NTN-NR". Three separate faults:

1. **Name matching breaks on hyphens.** The session-name-to-agenda matcher deletes "-" so "NTN-NR" becomes the single word "ntnnr", which matches no chair-notes title. So the name-only link that already exists never fires here.
2. **Two candidates.** Even with that fixed, "NTN" + "NR" fits both 9.4 "GNSS resilient NR-NTN operation" and 9.5 "NR NTN in systems using downlink compensation", so the "only on a unique match" rule refuses. But 9.5 is already listed explicitly in the same block, so the name must mean the other one (9.4).
3. **The "|" separator is ignored.** "|" closes the R20 head; "6GR (90)" starts a new head. Today 6GR (90) is read as an item inside R20, so R20's minutes don't add up (60 vs 20+90) and the block is not split, and the next items inherit the wrong group label.

## Expected result
- 14:00-14:40 NTN-NR -> 9.4 (R20)
- 14:40-15:00 9.5 NTN (R20)
- 15:00-15:40 10.7.1 NTN (6GR)
- 15:40-16:30 10.3.1 Channel coding (6GR)

## Changes (general rules, no cell-specific fixes)
- `ingestion/topic_agenda_mapper.py`: split hyphenated words into tokens ("NTN-NR" -> ntn, nr) while still keeping the joined form; keep "nr" usable when it is part of the topic name. Accept an `exclude` set: codes already explicitly listed in the same block are removed from the candidates before the uniqueness check.
- `ingestion/block_schedule.py`: treat "|" (and a line starting with a new timed head after it) as the end of the current head, so "6GR (90)" opens a new head instead of being an item. A name-only timed item ("NTN-NR (40)") under a head stays an item and gets its code via the mapper, passing sibling codes as `exclude`.
- Group labels come from the head the item actually sits under (R20 vs 6GR).
- Update `ingestion/AGENTS.md` rule for topic mapping (hyphen tokens, sibling exclusion) and the granularity skill table (new cause: "pipe separator").

## Tests (exact cell text)
- Mapper: "NTN-NR" with 9.4/9.5 titles and 9.5 excluded -> 9.4; without exclusion -> no link (still refuses to guess).
- Block parse of the full cell -> the four blocks above with correct groups, no "minutes don't add up" warning.

## Verify
Run ingestion tests, rebuild RAN1#127, run the granularity audit and public-data check, then open the Schedule in the preview and confirm the four blocks and that filtering by 9.4 shows NTN-NR.
