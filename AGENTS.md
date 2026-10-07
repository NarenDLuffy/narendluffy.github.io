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
- Online canonical chair columns use the schedule cell colour as chair identity; explicit “Main session” or “RAN1 #number commences” text marks Main — avoids position and white-colour assumptions. Offline tables are always two positional columns (Offline Session 1/2), colour ignored; vertically merged cells repeat per block — offline colours don't identify chairs.
- ICS export uses meetingTimeZone() which maps fixed Etc/ offsets to real DST zones by city — calendars stay correct in summer.
- Venue mode UI is gated by VENUE_MODE_ENABLED in venueMode.ts (currently off) — plumbing kept for a future HTTPS venue server.
- Schedule and drafts workflows share the "data-refresh" concurrency group and rebase-retry on push — they commit to the same branch.
- Generated schedule/drafts data is read live from the GitHub repo copy (bundled copy as fallback) — updates appear without re-publishing.
- Schedule blocks with only a topic name get their agenda code from chair-notes agenda titles via ingestion/topic_agenda_mapper.py, linked only on a unique match — so agenda filters catch them without guessing.
