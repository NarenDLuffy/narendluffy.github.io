---
name: new-meeting-setup
description: Prepare RAN1 Live! for a meeting that has not started yet — discovery, dates, snapshots, the remote meeting server, and the checks that prove it is ready. Use when a new RAN1 meeting number appears, or when asked to get the app ready for the next meeting.
---

# New meeting setup

No code changes per meeting: discovery finds the meeting from the 3GPP portal and
both refresh jobs pick it up on their own. This is the checklist that proves the
app is ready.

1. **Discovery and dates.** After the next updater run the meeting must appear in
   `public/data/meetings.json` with correct dates, timezone and status
   `upcoming`:

   ```
   python3 -c "import json;print(json.dumps(json.load(open('public/data/meetings.json'))['meetings'][-2:],indent=1))"
   ```

2. **Snapshots.** Build the timetable and scan the drafts folder once:

   ```
   python -m ingestion.generate_schedule --meeting <new-slug-fragment>
   python -m draft_tracker.update_drafts --slug <new-slug>
   ```

   Before the week starts, only the per-meeting archive is read; the venue
   server and sync mirror are deliberately ignored until the meeting week,
   because they still hold the previous meeting's files.

3. **Remote meeting server.** The login (`MEETING_FTP_USER`, `MEETING_FTP_PASS`)
   is saved once in GitHub and is the same for every meeting — check it still
   exists, never re-add it. Only the host name changes each meeting: it is either
   entered by a delegate on the Drafts page, or read out of the meeting's own
   documents and stored only after a real login proves it. Never type an address
   from memory and never guess one.

4. **Checks.**

   ```
   bun run check:draft-merge
   node scripts/check-meeting-health.mjs --slug <new-slug>
   node scripts/check-public-data.mjs
   ```

   The health check may still report a missing remote source before the week:
   the address usually appears in the venue documents only close to the meeting.

5. **Publish only if the site changed.** New meeting data reaches the live site
   through the repo copy without a publish.

Related: `meeting-week-refresh` once it is running, `drafts-live-merge-check`,
`publish-and-verify`.
