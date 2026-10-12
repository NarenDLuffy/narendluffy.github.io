# Room colours and Online/Offline room tags

## What will change

- On the **Now** page, each current and upcoming session card will use its room’s established colour instead of the agenda/topic colour. The coloured edge and subtle card tint will match the same room in the timetable and Rooms page.
- Add **(Online)** or **(Offline)** to room names based on the room identity already produced by schedule ingestion, including the Main room when it comes from an online schedule table.
- Apply the room tag through the shared room-label helper so it appears consistently on Now, the timetable headings, Rooms, room detail pages, session details, and colleague-room references without duplicating label logic.
- Keep session labels such as **RAN1 Main** or **RAN1 Brk2** alongside the new mode tag, without repeating text already present in the room name.

## Verification

- Check RAN1#126bis specifically: the five merged rooms remain five, Yeongju names remain merged, and each displayed room has the correct Online/Offline tag.
- Verify the Now page visually on a phone-sized viewport: simultaneous sessions have distinct room colours, labels fit, and no text overlaps.
- Run the relevant frontend checks and confirm the preview has no errors.

## Technical details

- Extend `src/lib/rooms.ts` with one shared room-mode derivation from `chairLaneId`, and compose that into `roomLabel()`.
- Give `SessionCard` an opt-in room-colour presentation using the matching room from the schedule bundle; enable it for both **Happening now** and **Starting next** on `src/routes/index.tsx`.
- Preserve topic colouring elsewhere unless that view already uses room colours.