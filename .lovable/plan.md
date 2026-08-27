# Verify refresh pipelines end-to-end

Confirmed configuration (from workflow files):
- `update-drafts.yml`: every 5 min Mon–Fri 03:00–21:00 UTC, off-hours hourly; commits to `public/data`.
- `update-schedule.yml`: every 5 min Mon–Fri 05:00–19:00 UTC, hourly otherwise; commits to `public/data`.
- App-side: drafts refetch every 60 s, schedule every 5 min, plus manual "Refresh now".

## Steps

1. **Check recent workflow runs**: open GitHub → Actions on the repo and confirm `Track drafts` and `Update schedule` have recent green runs (not just queued — GitHub can delay `*/5` crons under load; 5–15 min lag is normal).
2. **Confirm commits land**: check the repo history for `chore(drafts):` / `chore(data):` bot commits with recent timestamps.
3. **Confirm GitHub sync from Lovable**: verify the repo's latest commit matches the current Lovable project state (two-way sync should be pushing automatically).
4. **Fix anything found**: if runs are failing (auth, parsing, push conflicts), diagnose and patch the workflow/ingestion code.

## Technical details

- GitHub cron minimum effective interval is ~5 min and best-effort; exact 5-min punctuality is not guaranteed by GitHub.
- If cron lag proves too slow during meeting week, an optional upgrade is a repository-dispatch trigger, but that needs an external pinger — only add if step 1 shows unacceptable lag.
