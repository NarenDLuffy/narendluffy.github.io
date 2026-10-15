# Cell-level "latest change" tracker for schedule conflicts

## Goal
When several schedule files (or two tables in one file) disagree about the same room and time, the version a chair **actually edited most recently** wins. Leftover copies that nobody touched no longer win on vote count. Example: Thursday 12:30–13:00 Room 201. Main v04 changed it to 10.5.3.4. Sorour v01 and Hiroki v06 still carry the old 10.5.3.2. Today the two old copies out-vote the main file. After this change, 10.5.3.4 wins.

## How it works
1. For each schedule file family we use (main, Sorour, Hiroki, chair notes), also fetch the **previous revision** (v_{N-1}). If it is missing, fetch the nearest older one that exists.
2. Parse both versions the same way. Compare them **cell by cell**: same table, same day, same room and time.
3. Mark each cell in the latest version as:
   - **edited**: the text differs from the previous version, or the cell is new;
   - **unchanged**: identical to the previous version;
   - **unknown**: no previous version exists (first release, v00).
4. Every timetable block inherits its cell's mark and the time that revision was published.
5. When blocks compete for the same slot, the new order is:
   1. Edited beats unchanged. Among edited blocks, the most recently published revision wins.
   2. Then the existing rules: the chair's own table, then file count, then detail, then number of items.
6. The losing version stays visible as a note, as it is today: "Another schedule file lists 10.5.3.2 here (older copy)".

## Corner cases
- **First release (v00) or missing previous file**: marked unknown, so the current rules apply. Unknown never beats edited.
- **The same file edits both of its tables in conflicting ways**: the grid wins on order and timing (grid vs detail tie-breaker). The detail table only adds finer splits for the same items. The block gets a note.
- **Two different chairs edit the same slot**: the more recently published revision wins. If both were published at the same moment, the chair's own table wins, then the existing order. Always noted.
- **Small text-only edits** (spaces, a dash type, "10.5.3.x" vs "10.5.3.X", a reordered colour legend): text is normalised before comparing. Only changes to time, items, minutes or room count as edits.
- **Rows or tables added or removed in the new version**: cells are matched by day, time, room and lane colour, not by row number, so an inserted row doesn't mark everything below it as edited.
- **A typo fix** (the "Sensing (6)" → "(60)" kind) counts as an edit. That is correct: it is the chair's newest intent.
- **A revision that is skipped or withdrawn** (v05 missing, v06 present): compare against the newest older revision that exists.
- **Draft → official switch** (Draft v03 → official v00): the official file's previous version is the last Draft of the same family, so v00 still gets a real comparison.
- **An item removed in the new version**, e.g. struck through: if the old copies still list it, the edited block without it wins, and the old version is shown as a note only.
- **The same file in two folders**: deduplicated first, as today, so it is never compared with itself.
- **Edits are not remembered between revisions**: the comparison is always latest vs previous. If v05 edits a cell and v06 leaves it, the cell is unchanged in v06, and a stale copy could win again. To prevent this, keep a small **edit history** per slot: last edited in revision N at time T. "Most recently edited" then means the latest edit across all revisions seen, not only the last one.

## Optimisations
- **Cache parsed revisions**: save each parsed revision (keyed by file content fingerprint) in the cache the GitHub job already keeps. Each old revision is then downloaded and parsed once per meeting, not on every 5-minute run.
- **Store the edit history** with the meeting's published data, so each run only compares the newest revision against the stored history and never re-walks every older version.
- **Fetch nothing new when nothing changed**: if no file's fingerprint changed since the last run, skip the comparison completely.
- **Only compare contested slots**: the tracker matters only when two or more blocks compete for one slot. Uncontested slots keep the old path, so the cost stays small.
- **Limit the look-back** to one older revision per family on each run. Older history comes from the stored record.

## Checks and visibility
- Tests built from the real cells:
  - Thursday Room 201: 10.5.3.4 wins.
  - Friday morning: the order the chair actually edited wins.
  - v00 falls back to the existing rules.
  - A skipped revision compares against the newest older one.
  - An inserted row doesn't mark unrelated cells as edited.
  - A cell edited in v05 and untouched in v06 still beats the stale copies.
- The Ingestion status page and "Verify data" list each contested slot that was decided by "latest edit", naming the revision that won, so you can check it.
- The ingestion rules note and the meeting-week-refresh skill describe this rule.

## Technical details
- `ingestion/live.py`: `_latest_revisions` also returns the predecessor for each family, using the same family and Draft→official rules. `parse_schedule_sources` parses the predecessor through the same parsers and keeps it out of the published output.
- New `ingestion/revision_diff.py`:
  - Builds a normalised cell key from (date, room lane colour/chair lane, start, end) using `SessionSourceRef.cell`.
  - Normalises the value (agenda codes via `_base_code`, minutes, start and end).
  - Produces `edited | unchanged | unknown` plus `editedAt`.
  - Merges the result with the stored history in `public/data/meetings/<slug>/edit-history.json`.
- `SessionSourceRef` gains `edit: str | None` and `editedAt: str | None` (optional, backward-compatible). `CandidateBlock` carries the best of its refs.
- `canonical_schedule._resolve_same_slot`: the sort key becomes `(-edit_rank, -editedAt, -_own, -len(sourceIds), -specificity, -len(agendaItems))`. The same edit rank feeds the "Another schedule table lists…" tiling tie-break.
- Parsed-revision cache keyed by `contentHash` under the existing Actions cache path.
- Tests: `ingestion/tests/test_revision_diff.py`, plus additions to `test_canonical_schedule.py`. Rebuild 126-bis and confirm with `check-meeting-health.mjs` and `audit_granularity.py`.
- Update `ingestion/AGENTS.md` (one rule) and the meeting-week-refresh skill.
