---
name: schedule-granularity-audit
description: Find and fix every place the published RAN1 timetable shows less detail, wrong times or gaps compared with ANY chair's schedule DOCX. Use after each new chair-file version, or when a user says a chair file "has better granularity", a block is "not split", ".x shown", "minutes wrong", or "gap".
---

# Schedule granularity audit

Goal: the user never has to point out a mis-read chair cell. Applies to every
chair/sub-chair schedule file, not one person's.

## Steps

1. Rebuild the meeting: `python -m ingestion.generate_schedule --meeting <slug-fragment>`.
2. Audit: `python -m ingestion.audit_granularity --meeting <slug-fragment>`.
   It lists, with a cause tag, every
   - **coarser** block: a document splits a published block into ≥2 timed parts
     (`live.granularity_checks`, also shown as "Less detail than the chair file"
     on the Ingestion status page and in Verify data),
   - **gap**, and **cell** refusal.
   Exit 0 + "no mismatches" = done.
3. For each line, read the real cell: download the file named in the message
   and print `_sessions_for_cell` input/output for that room/day (wrap the
   function and filter by `day_date`, `room.roomName`, `block_start`).
4. Match the cause and apply the fix pattern below. Add a test in
   `ingestion/tests/` using the **exact cell text**. Run `python -m pytest -q ingestion/tests`.
5. Rebuild and audit again until clean; run `node scripts/check-public-data.mjs`.

## Known causes and fix patterns (all in `ingestion/`)

| Cause | Symptom | Fix pattern |
| --- | --- | --- |
| range-minutes | "Maintenance (90-120)" kept whole or mis-timed | `RANGE_DURATION_RE` head; items' sum must fall in the range (`_Segment.min_minutes`) |
| bare-codes | "7 pre-Rel-19 CRs (50)", "11 TEI20" lose their item | `LEADING_CODE_RE`/`_item_codes`, only at the start of a timed line under a head |
| several items on one line | "7 …, 8.2 … (50)" keeps only one code | `_Slot.codes`; single-slot breakdown keeps all `agendaItems` (canonical) |
| wildcard-x | `10.5.4.x` stays one block though children are timed | `canonical_schedule.is_descendant` / `_base_code` |
| continuation rows | another room's items appear, gaps | never re-read vertical-merge continuation cells |
| typo minutes | "Sensing (6)" in a 90-min block | block stays whole with "Minutes don't add up" note, and **loses** to any chair tiling (`_drop_overlaps`) |
| grid copy beats chair table | chair's detail ignored, coarse block wins | ranking in `_drop_overlaps` / `_resolve_same_slot` (`_own`, specificity) |

A new cause: name it, add a row here, a test, and the general fix.

## Never

- Invent times: split only when stated minutes fit.
- Relax a check (coverage gaps, cell checks, granularity) to make a run pass.
- Fix one cell by name/room/chair; fix the rule.
