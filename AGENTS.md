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
