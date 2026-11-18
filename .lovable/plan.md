# Connect RAN2 "My agenda" to the schedule and Drafts

## Why nothing shows up today
I checked the RAN2#136 data and found three separate gaps:

1. **Matching only goes one way.** My agenda lets you follow leaf items only (e.g. 8.2.4 "Topology 2"). RAN2's schedule often names only the parent topic (e.g. "NR20 AIoT" → 8.2). The schedule filter accepts "session is the item or one of its children", so a session marked 8.2 never matches a followed 8.2.4. RAN1 rarely hits this because chair notes list leaf items.
2. **Many blocks have no agenda item.** 45 of 116 RAN2 sessions are named by topic only ("ISAC offline (Xiaomi)", "RRC modeling (Samsung)", "A-IoT offline", "CB Kyeongin", "UP offlines"), so they can never match anything.
3. **Draft folders are not linked to agenda items.** RAN2 folders use tags like `[AT136][401][AIoT] ...` or `[MOB]` instead of agenda numbers, so all 32 folders are currently "unmapped".

## What will change
- **Parent blocks count for their children:** a block marked 8.2 shows when you follow any 8.2.x item (same idea as the existing 10.4.x rule). This applies to all groups, as RAN1's ".x" rule already does. Highlighting stays the same.
- **Name-only blocks get agenda items:** for RAN2, match the block's topic words against the RAN2 agenda titles (e.g. "RRC modeling" → 9.3.2.1, "A-IoT" / "AIoT" → 8.2, "ISAC" → its ISAC item, "UP" → 9.3.1). Only clear, single best matches are used; unclear ones (e.g. "offlines", "CB Kyeongin") stay unlinked and are listed in Verify data, never guessed.
- **Draft folder tags get agenda items:** map RAN2 tags (`AIoT`, `MOB`, `AI-MOB`, `6G UP`, `6G RRC modeling`, `R20 IoT NTN`, `Maint`, `TEI20`, ...) to agenda items using the same title matching, with a small explicit tag table for abbreviations (MOB, LPWUS, Maint) that titles don't spell out.
- **Verify data** for RAN2 shows how many blocks and draft folders remain unlinked.

## Checks
- Tests: following 8.2.4 shows the "NR20 AIoT" (8.2) block; following 9.3.2.1 shows "RRC modeling (Samsung)"; `[AT136][401][AIoT]` maps to 8.2; "offlines" stays unlinked; RAN1 matching results unchanged.
- Rebuild RAN2#136, then in the browser switch to RAN2, follow a few items and confirm Schedule, Now and Drafts show them.

## Technical details
- `src/services/scheduleService.ts` `agendaMatches`: also true when `filter.startsWith(code + ".")` (session is an ancestor of the followed leaf); reuse in `presenceService` follow counting.
- `ingestion/ran2_schedule.py`: after parsing, run name-only mapping against `parse_agenda_docx` titles (token overlap with a clear-best-match margin, mirroring RAN1's name-only rule); record unmatched in health notes.
- `draft_tracker/update_drafts.py` and `src/services/draftLiveSource.ts` `agendaFromPath`: for RAN2, parse the bracketed tag and resolve via a shared tag→agenda table plus title matching; agendaMethod "tag".
- Add pytest + vitest cases; update `ingestion/AGENTS.md` with the ancestor-match and tag-mapping rules.
