# Make "Verify data" fail only on real problems, and keep the timetable refreshing

## What is checked (live GitHub data, 15:30 UTC)
- The timetable now uses **Hiroki v05** and Chair notes v05 (rebuilt 12:39 UTC).
- Wednesday Room 201: Sensing is no longer 09:30–09:36. The "(6)" typo no longer adds up, so the block shows Hiroki's full 09:00–10:30 slot (Waveform + Sensing) with the note "Minutes don't add up: items total 36 min, block is 90 min."
- "Verify data" fails for one reason only: **no remote meeting server address has been entered**. Everything else passed. That is a missing optional source, not broken data — the timetable and drafts are fresh.
- The timetable updater ran at 03:32, then not again until 11:44, even though it is scheduled every 5 minutes. GitHub skips scheduled runs when it is busy, so there were 8 hours with no refresh.

## Steps
1. **Missing remote address = note, not failure.** The check still prints it every time, but the job only fails on real problems: stale timetable or drafts, a Draft-only timetable, a server address that was entered but doesn't answer, or a missing login.
2. **Catch silent gaps.** The check fails when the timetable or drafts have not been refreshed for more than 2 hours during session hours of the meeting week (6 hours outside them). An 8-hour gap like this morning's would then fail loudly.
3. **Back-up trigger.** When "Verify data" sees a stale timetable, it starts the "Update schedule" and "Track drafts" jobs itself, so a skipped GitHub schedule repairs itself within 30 minutes.
4. **Small blocks.** Add the health warning planned earlier: any timetable block shorter than 10 minutes shows on the Ingestion status page (as a note, not a failure).
5. Run the check locally against today's data (it should pass with notes), then trigger "Verify data" once on GitHub and confirm it is green.

## Technical details
- `ingestion/health.py`: `skipped-no-host` becomes level `info`; `unreachable` and `skipped-no-credentials` stay `warn`. Add a short-block info warning from the schedule section (count of sessions with duration < 10 min).
- `scripts/check-meeting-health.mjs`: freshness limit 2 h when the meeting is active and the time is within 05–19 UTC on weekdays, otherwise 6 h; `HEALTH_MAX_AGE_HOURS` still overrides.
- `.github/workflows/verify-data.yml`: `permissions: actions: write`; on a stale result, `gh workflow run update-schedule.yml` / `update-drafts.yml` before failing.
- Record in roadmap.md; skills drafts (drafts-live-merge-check, new-meeting-setup, publish-and-verify) still need activating.
