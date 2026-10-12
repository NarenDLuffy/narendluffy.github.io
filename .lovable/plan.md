# Room colours and Online/Offline grouping

## What will change

- On the **Now** page, each current and upcoming session card will use its room’s established colour instead of the agenda/topic colour. The coloured edge and subtle card tint will match the same room in the timetable and Rooms page.
- On each Now card, show a compact **Online** or **Offline** tag beside the room name. This keeps the mode attached to the room and avoids crowding the agenda list.
- On the full **Schedule**, group the existing room columns under two spanning headings: **Online** and **Offline**. The room columns, individual room colours, session blocks, horizontal scrolling, filtering, and selection remain unchanged beneath those headings.
- Treat the Main room as Online when its room identity comes from an online schedule table. Keep any room that lacks reliable mode evidence outside either forced classification rather than guessing.

## Verification

- Check RAN1#126bis specifically: the five merged rooms remain five, Yeongju names remain merged, and each room appears under the correct Online/Offline heading.
- Verify the Now page visually on a phone-sized viewport: simultaneous sessions have distinct room colours, mode tags fit beside room names, and no text overlaps.
- Verify the grouped Schedule header on phone and desktop widths, including horizontal scrolling and sticky headings.
- Run the relevant frontend checks and confirm the preview has no errors.

## Technical details

- Extend `src/lib/rooms.ts` with one shared room-mode derivation from `chairLaneId` so both views use the same classification.
- Give `SessionCard` an opt-in room-colour and room-mode presentation using the matching room from the schedule bundle; enable it for both **Happening now** and **Starting next** on `src/routes/index.tsx`.
- Update `Timetable` with a two-level sticky header whose group widths are calculated from the existing room-column widths, including parallel lanes.
- Preserve topic colouring elsewhere unless that view already uses room colours; do not append mode text to every room name across the app.