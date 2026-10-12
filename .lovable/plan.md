# Room colours and Online/Offline grouping

## What will change

- On the **Now** page, each current and upcoming session card will use its room’s established colour instead of the agenda/topic colour. The coloured edge and subtle card tint will match the same room in the timetable and Rooms page.
- On each Now card, show a compact **Online** or **Offline** tag beside the room name. This keeps the mode attached to the room and avoids crowding the agenda list.
- On the full **Schedule**, group the existing room columns under two spanning headings: **Online** and **Offline**. The room columns, individual room colours, session blocks, horizontal scrolling, filtering, and selection remain unchanged beneath those headings.
- Classify rooms directly from their source table: a room from an Online table is **Online**, and a room from an Offline table is **Offline**. This includes the Main room when it is in the Online table; no name-based guessing is used.

## Verification

- Check RAN1#126bis specifically: the five merged rooms remain five, Yeongju names remain merged, and each room appears under the correct Online/Offline heading.
- Verify the Now page visually on a phone-sized viewport: simultaneous sessions have distinct room colours, mode tags fit beside room names, and no text overlaps.
- Verify the grouped Schedule header on phone and desktop widths, including horizontal scrolling and sticky headings.
- Run the relevant frontend checks and confirm the preview has no errors.

## Drafts: refresh both meeting-week sources

- During the meeting week, check both the HTTPS venue server at **10.10.10.10** and **MEETINGS_SYNC** on every live refresh instead of stopping after the first source that answers.
- Merge files from both successful reads into one Drafts list using the existing document identity, so replication of the same upload stays one file while a newer or source-only upload is retained.
- Keep the published snapshot as the fallback when neither live source answers. Once venue or MEETINGS_SYNC provides a valid current-meeting listing during meeting week, hide files whose only source is the per-meeting archive folder; that archive can contain earlier material which is no longer part of the live drafts tree.
- Remove archive-only folders and their old change notices from the displayed meeting-week result as well, so counts and unread badges do not retain entries such as the old 10.8.1 Round 1 files.
- An unavailable venue server remains normal; MEETINGS_SYNC is still checked and the page continues working.
- Report the sources honestly in the Drafts refresh status, including when both contributed files.

## Technical details

- Extend `src/lib/rooms.ts` with one shared room-mode derivation from `chairLaneId` so both views use the same classification.
- Give `SessionCard` an opt-in room-colour and room-mode presentation using the matching room from the schedule bundle; enable it for both **Happening now** and **Starting next** on `src/routes/index.tsx`.
- Update `Timetable` with a two-level sticky header whose group widths are calculated from the existing room-column widths, including parallel lanes.
- Preserve topic colouring elsewhere unless that view already uses room colours; do not append mode text to every room name across the app.
- Refactor `probeLiveDrafts()` so all eligible meeting-week candidates are checked, successful results are merged cumulatively, and the direct MEETINGS_SYNC read remains only a fallback for its server-assisted read rather than a duplicate crawl.
- Identify archive-only published entries from their saved source URLs, without relying on filenames or agenda numbers; preserve any document also present on venue or MEETINGS_SYNC.
- Add focused checks for venue-only, sync-only, both available with overlapping files, neither available, and removal of archive-only files/folders/events once a live source answers.