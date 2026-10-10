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
- Rooms are one per (online|offline, cell colour) across ALL schedule files, merged in ingestion/room_resolver.py; names come from any file (colour legend above a table, one-room table headings) and never create a column alone; explicit “Main session”/“RAN1 #N commences” marks Main — no chair names, room counts or positions are hard-coded.
- Schedule times are never invented: a block splits only when items have stated minutes that fit; otherwise it stays one block listing its items (stated minutes kept, mismatch noted). Same-slot claims from several files resolve to the most detailed, chairs' own tables ranked above copies of the shared grid.
- ICS export uses meetingTimeZone() which maps fixed Etc/ offsets to real DST zones by city — calendars stay correct in summer.
- Venue mode UI is gated by VENUE_MODE_ENABLED in venueMode.ts (currently off) — plumbing kept for a future HTTPS venue server.
- Schedule and drafts workflows share the "data-refresh" concurrency group and rebase-retry on push — they commit to the same branch.
- Generated schedule/drafts data is read live from the GitHub repo copy (bundled copy as fallback) — updates appear without re-publishing.
- Schedule blocks with only a topic name get their agenda code from chair-notes agenda titles via ingestion/topic_agenda_mapper.py, linked only on a unique match — so agenda filters catch them without guessing.
- DOCX schedule ingestion reads only active visible Word runs: highlighted and inserted text stays, while deleted, hidden, and struck-through text is excluded — withdrawn agenda items must never enter the canonical schedule.
- Live drafts from the venue server and Meetings Sync count only during the meeting's week (±1 day), ignoring files older than 14 days before start — the previous meeting's leftovers carry no meeting number.
- The remote meeting FTP host is stored once per meeting in the backend (first delegate to enter it wins) and read by GitHub Actions via /api/public/meeting-ftp-host; FTP login comes from GitHub secrets — browsers can't speak FTP and the host changes each meeting.
