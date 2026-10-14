# Read every chair schedule's finer breakdown (Hiroki v06 is the first example), and catch this kind of miss automatically

## What is wrong now (checked in the saved Wednesday data)

Yeongju B Hall, Wed 14 Oct, shows one block **14:30–16:00 "TEI, AI 7/" (8.2)** and then **16:00–16:30 R20 Coverage RRC**. v06 says:

```text
Maintenance (90-120)
  8.2 R19 LP-WUS, R19/20 Mobility (30)
  7 pre-Rel-19 CRs, 8.2 R19 Duplex (50)
  11 TEI20 (10)
R20 Coverage RRC (30)
```

So the times should be 14:30–15:00, 15:00–15:50, 15:50–16:00, then 16:00–16:30. The saved block has no breakdown, no cell reference, and is marked "inferred-duration". That means the v06 detail cell was not used. The grid copy was used instead.

## Likely causes (to confirm in step 1, one by one)

1. **Range minutes aren't read.** The minutes reader only accepts one number like "(30)". "(90-120)" is not read, so "Maintenance" never becomes a timed head that the three items fill.
2. **Single-number agenda items aren't codes.** The code reader needs a dot, so "7 pre-Rel-19 CRs" and "11 TEI20" are not seen as items 7 and 11. In the topic, "AI 7/8.2" was cut to "TEI, AI 7/".
3. **Lines that name several items.** "8.2 R19 LP-WUS, R19/20 Mobility (30)" is one timed line with free text. It may be split or dropped.
4. **Because no detail was found,** the grid's broad block wins, and nothing reports that a more detailed file was ignored.

## Fix

- Read "(a-b)" minutes as a range: it is a container and never forces a split by itself. The items' own stated minutes decide the times, if they fit the cell (30+50+10 = 90, inside 90–120).
- Accept bare top-level codes ("7", "11") **only at the start of a timed item line under a head**, so plain numbers in text are not mistaken for codes.
- Keep a timed line with several items as one slot. List all its codes ("8.2", "7, 8.2") and keep the original label.
- Times are still never invented. If the minutes don't fit, the block stays whole with a note (unchanged rule).

## Categorical check: "a detailed file said more than we published"

A new validator check runs on every rebuild. For each published block, it compares the block with every eligible document's cell for the same room and time. It flags a block when a document lists **more timed items** or **finer codes** than the published block shows, or when the block has no cell reference even though a chair's own table covers that time. These flags are warnings on the Ingestion status page and in Verify data, and they come with the document's cell text. A dropped breakdown can then never pass without anyone seeing it.

On top of that, a one-time audit runs over **all** 126-bis blocks with v06, Sorour v01, and the official v00. It produces a list of every mismatch, sorted into the causes above (or any new one found). Each cause gets a fix plus a test made from the real cell text.

## Skill for next meeting

Add a new skill, **schedule-granularity-audit**. It runs the audit, reads the mismatch list, sorts each mismatch into one of the known causes (range minutes, bare codes, several items on one line, wildcard `.x`, continuation rows, typo minutes like "Sensing (6)", grid copy beating chair table), applies the fix pattern for that cause, and checks again. Link it from meeting-week-refresh so it runs after every new chair-file version.

## Verification

- Tests built from the exact v06 Yeongju B cell, plus range-minute, bare-code and several-items-on-one-line cases. All existing tests still pass.
- Rebuild 126-bis. Yeongju B Wed should show 14:30–15:00 / 15:00–15:50 / 15:50–16:00 / 16:00–16:30. The audit should show zero unexplained mismatches. Earlier fixes stay intact: Tamna BC evening, 10.5.4.x children, Sensing.
- Check the timetable in a phone-sized browser.

## Technical details

- `ingestion/block_schedule.py`: extend `DURATION_RE`/`_split_head` for ranges (store as max with a `range` flag, container-only), add bare top-level codes for item lines, keep multi-code timed lines as one slot.
- `ingestion/live.py` + `validator.py`: new `granularity_checks` that compares published blocks with per-document parsed cells (via `SessionSourceRef.cell`).
- New script `ingestion/audit_granularity.py` for the full report. New skill under the skills folder. Record the rule in AGENTS.md. Update roadmap.md.
