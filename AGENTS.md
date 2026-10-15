<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->
- Sync-mirror schedule files belong to a meeting only when their name matches its number and bis suffix (unlabelled files only while the meeting is active) — prevents the previous meeting's rooms leaking into the next.
- Room colours, labels ("Name (RAN1 BrkN)") and active-room filtering go through src/lib/rooms.ts — one place for room presentation.
- ICS export uses meetingTimeZone() which maps fixed Etc/ offsets to real DST zones by city — calendars stay correct in summer.
- Venue mode UI is gated by VENUE_MODE_ENABLED in venueMode.ts (currently off) — plumbing kept for a future HTTPS venue server.
- Schedule and drafts workflows share the "data-refresh" concurrency group and rebase-retry on push — they commit to the same branch.
- Generated schedule/drafts data is read live from the GitHub repo copy (bundled copy as fallback) — updates appear without re-publishing.
- The remote meeting FTP host is stored once per meeting in the backend (first delegate to enter it wins) and read by GitHub Actions via /api/public/meeting-ftp-host; FTP login comes from GitHub secrets — browsers can't speak FTP and the host changes each meeting.
- Schedule documents: an official file (no "Draft" prefix) supersedes every Draft revision of the same family, regardless of version — chairs publish the official copy at meeting start.
- Live drafts merge reconciles against the live tree during the meeting week: a snapshot file the live server no longer lists is hidden, never deleted, and only when the crawl actually opened its containing folder; crawl and snapshot share the Inbox/drafts root so one upload stays one artifact.
- Source folders follow one date rule shared by timetable and drafts (remote_ftp.meeting_phase / meetingPhase): meeting folder up to the day before, Meetings Sync only on meeting days, both on the day after — Meetings Sync holds the previous meeting's files until the week, and the meeting folder lags during it.
- The backend job /api/public/jobs/schedule-watch (every 5 min) dispatches update-schedule.yml when Meetings Sync holds a schedule DOCX newer than health.lastAttemptAt — GitHub's own cron drops runs for hours.

- ingestion/ has its own AGENTS.md (schedule parsing and canonical rules) — read it before changing files there.
