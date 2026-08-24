# Schedule accuracy audit + drafts from the venue-local server

## What I checked first

- Generated RAN1#126 data has 218 sessions (Mon 41, Tue 58, Wed 54, Thu 49, Fri 16).
- The Monday `0.6/0.7 Madrid/Lisbon` column is attributed entirely to "Xiaodong"; the only Monday "Sensing" block landed in `1.1 Himalaya`. The source document mentions Sensing 8 times, and only 6 sensing blocks exist in the generated data.
- 58 generated sessions carry no agenda code at all (topic text only), so per-item coverage cannot currently be verified by eye.
- Drafts: `src/services/draftService.ts` reads only the published JSON index. It never probes the venue-local server, and `draft_tracker/local_source_interface.py` is a stub that always reports "unavailable". So no, drafts do not see 10.10.10.10 today — only the schedule has that path.

Root cause for the missing/misplaced Monday block is not yet proven; the likely candidate is the mapping from floating room/chair labels (x-offsets) to grid columns in the offline table, which would shift a whole column's room and lead. Step 1 confirms this before any parser change.

## Part 1 — Prove and fix schedule correctness

1. **Audit harness** (`ingestion/audit_schedule.py`): walk every cell of every day/room block in the week-grid document, extract each agenda-item line with its duration, and diff against the generated `schedule.json`. Report:
   - items present in the document but missing from the schedule,
   - items whose room, day, lead, or duration differ,
   - sessions in the schedule with no counterpart in the document.
   Run it for the Maastricht document and print a per-day summary.
2. **Fix what the audit reports**, in this order:
   - column ↔ floating room label alignment (room and chair assignment per column, per table, per day),
   - cell segmentation so every agenda line becomes its own timed block (no swallowed lines, no zero-length blocks),
   - agenda-code extraction for the 58 code-less sessions, so `10.8 Sensing (80)` yields both the code and the label.
3. **Re-run the audit until the missing/mismatched list is empty** (except items the document genuinely leaves ambiguous, which get listed in the run output).
4. Regenerate `public/data/meetings/ran1-126/*` and verify the Monday offline column in the preview.

## Part 2 — Drafts from the meeting-local server

The public 3GPP tree lags the venue server during meeting week. GitHub Actions can never reach 10.10.10.10, so this has to run in the browser, mirroring what the schedule already does:

- Add a local-source probe to the drafts service using the existing `LocalSourceTransport` abstraction and the base URL already configured in Settings/Source panel.
- When a local drafts index is reachable and genuinely newer (higher revision or newer file timestamps per artifact), merge it over the published index instead of replacing it, so nothing already known is lost.
- Deduplicate by normalized path + revision so a document seen locally and later publicly stays one artifact with one unread state.
- Show origin and freshness in the Drafts header ("venue server · updated 17:04" vs "public tree · updated 12:00"), and never surface an unreachable venue server as an error.
- Keep the Python-side stub as-is; add a comment recording that local ingestion is browser-only by design.

## Technical notes

- `ingestion/block_schedule.py` holds the grid parser; room labels come from `posOffset` on floating textboxes, matched to table grid columns.
- Drafts changes touch `src/services/draftService.ts`, `src/hooks/useDrafts.ts`, `src/routes/drafts.index.tsx`, and reuse `src/services/localSource.ts` transport plumbing.
- No backend or schema changes; all data stays static JSON plus device-local state.
