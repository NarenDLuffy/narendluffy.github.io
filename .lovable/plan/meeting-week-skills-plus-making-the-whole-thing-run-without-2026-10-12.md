# Meeting-week skills, plus making the whole thing run without you

## What you get

1. Four saved playbooks (skills) for the recurring work, so any future session follows the same checked steps instead of being talked through it again: **meeting-week refresh**, **drafts live-merge check**, **new meeting setup**, **publish and verify**.
2. Clockwork: the updater already runs on its own for every meeting — what's missing is that it stays quiet when something is off. After this, every run writes a small health record and a daily verify pass fails loudly, so a stale timetable, a duplicate drafts list or a missing remote-server address shows up as a warning on the Ingestion status page and a red GitHub run, not as you noticing it.

Nothing here needs you to do anything per meeting except, at most, one line in the app.

## Part 1 — The four skills

Each is written to the project's skills folder and then activated. Shape for all four: when it fires, the steps with a success check after each one, and the known failure modes with the fix.

| Skill | Fires on | Steps it captures |
| --- | --- | --- |
| `meeting-week-refresh` | "refresh the schedule", "rebuild 126-bis", "the timetable looks stale" | Confirm the meeting's dates and status → rebuild that meeting only (`python -m ingestion.generate_schedule --meeting <id>`, or the workflow's manual run with the meeting field) → confirm the timetable's timestamp moved, the room count held, and the official schedule file (not a Draft) is listed as the source → run the public-data guard |
| `drafts-live-merge-check` | "drafts look wrong", "duplicated", "old files still showing" | `bun run check:draft-merge` (18 checks) → `bun run check:draft-merge-live` against the real server → confirm zero duplicate documents, the hidden-file count is explained, and every folder in the tree was actually opened → read back `scanState` and the last successful scan time |
| `new-meeting-setup` | "next meeting", "a new meeting folder appeared" | Confirm the new meeting was discovered with correct dates → confirm its timetable and drafts snapshots appear → confirm the remote-server login is still saved and its address is entered for this meeting → run both checks above → publish only if the site itself changed |
| `publish-and-verify` | "publish", "is it live on ran1.app" | Read the security scan → publish → wait about a minute → open the changed page on ran1.app in a phone-sized browser and confirm the change plus no console errors → confirm that data-only changes need no publish at all |

The setup skill points at the other three rather than repeating them.

## Part 2 — Clockwork, so you don't comment every meeting

Already automatic, verified in the code:

```text
update-schedule.yml   every 5 min, Mon-Fri 05:00-19:00 UTC, hourly otherwise
update-drafts.yml     every 5 min, Mon-Fri 03:00-21:00 UTC, plus weekend/night passes
                      both: discover meetings themselves, one commit queue,
                      rebase-and-retry, 45-min timeout, single-meeting rebuild option
data                  the app reads the repo copy live, so refreshes appear without publishing
```

What still needs a nudge, and the fix:

1. **Silent failures become visible.** Every run writes a per-meeting health record: last successful timetable and drafts refresh, which source files were used, room count, whether the remote FTP source was read or skipped and why, how much of the drafts tree was actually opened, and how many files were hidden. The Ingestion status page shows it as a short "Last refresh" line plus a warnings list. Today a skipped remote source looks exactly like a healthy run.
2. **A daily verify pass that fails loudly.** One more scheduled job runs the ingestion tests, both drafts checks, the public-data guard, and a freshness assertion during meeting week (the timetable must have been rebuilt within a few hours). A regression then surfaces as a failed run rather than a broken page.
3. **The one manual line, made hard to miss.** The remote-server address stays never-guessed, but: if a meeting document states the address, the updater tests a real login and only then stores it automatically; otherwise the existing Drafts card and the new status-page warning both name it. The two GitHub logins remain a once-ever action.

## Technical details

- New `ingestion/health.py`: builds and writes `public/data/meetings/<slug>/health.json`; called at the end of `generate_schedule` and the drafts scan so it always reflects the last real attempt, including failures.
- `src/routes/admin.tsx` (Ingestion status): renders the health record — refresh times, sources, remote-source state, warnings — above the existing documents and conflicts sections.
- New `scripts/check-meeting-health.mjs`: asserts the health record is fresh and warning-free for the active meeting; used by the verify job and available to run by hand.
- New `.github/workflows/verify-data.yml`: daily pass (tighter during meeting week) running `python -m pytest ingestion/tests`, `bun run check:draft-merge`, `bun run check:public-data`, and the health assertion; fails loudly.
- `ingestion/remote_ftp.py`: adds a document-derived host candidate, login-verified before it is used, stored through the existing endpoint so the app shows it; falls back to the in-app card. No address is ever guessed.
- Four `SKILL.md` files under the project's skills folder, each activated after writing.
- `AGENTS.md`: one rule that the health record is the single source of pipeline truth for the status page, and one that a remote-server address is stored automatically only after a successful login.
- `roadmap.md` updated with these tasks.

## How it gets verified

- Run each check locally and confirm it passes.
- Trigger one manual updater run for RAN1#126-bis and confirm the health record appears and the status page renders it.
- Open `/admin` and `/drafts` in a phone-sized browser: no console errors, warnings shown when a source is skipped.
- Publish once at the end (the site changes), then confirm on ran1.app.

## What stays manual, and why

- The two GitHub logins: added once, ever.
- Turning on notifications on each phone: per device, cannot be done from the server.
