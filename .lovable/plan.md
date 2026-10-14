# Use stated child timings instead of .x containers

## Verified problem

Hiroki’s published v05 document contains the four stated durations in its detailed table: `10.5.4.2(20), 10.5.4.1(30), 10.5.4.4(30), 10.5.4.3(40)`, under `6G 10.5.4.x (120)`.

The saved Wednesday schedule instead publishes one `10.5.4.x` block from 17:30 to 19:30. The parser recognizes the four timed children in this cell, but the child-replacement check incorrectly uses the literal prefix `10.5.4.x.` instead of normalizing `10.5.4.x` to its parent branch `10.5.4`; another matching check already strips `.x`, so this is inconsistent handling, not the intended rule. This prevents the detailed blocks from replacing the container. Wildcard and leaf codes also currently receive the same depth score.

## Correction

- Treat a terminal `.x` as its parent branch when comparing schedule containers and children, including specificity and overlap resolution.
- Apply the same relationship when parsing a timed wildcard parent followed by timed children, so the parent duration is not counted twice.
- Preserve the chair’s stated order and minutes; never split a block using guessed durations or agenda-tree children alone.
- Keep `.x` when no valid timed breakdown exists. Keep untimed or mismatched breakdowns together with their stated minutes and existing warning behavior.
- Leave My agenda selection and wildcard filtering unchanged.

## Verification

- Add regression tests for wildcard containers with timed children from another document, same-cell wildcard parents, partial breakdowns, unrelated branches, untimed items, and mismatched totals.
- Rebuild RAN1#126bis from the latest eligible sources and require the existing room, cell, gap, and timing checks to pass.
- Confirm Wednesday’s Yeongju B Hall shows:
  - 17:30–17:50: 10.5.4.2
  - 17:50–18:20: 10.5.4.1
  - 18:20–18:50: 10.5.4.4
  - 18:50–19:30: 10.5.4.3
- Check the displayed timetable and followed-item results against the rebuilt data; verify existing corrected Sensing and Tamna BC blocks remain intact.

## Technical details

Update the parent/child and specificity rules in `ingestion/canonical_schedule.py`, and reuse equivalent wildcard-aware ancestry in `ingestion/block_schedule.py`. Add focused tests in the existing ingestion test files. Regenerate only the requested meeting’s data and record the general rule in `AGENTS.md`.