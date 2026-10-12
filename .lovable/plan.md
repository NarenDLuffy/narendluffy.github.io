# Online/Offline room presentation

## What will change

- On the **Now** page, each current and upcoming session card will use its room’s established colour instead of the agenda/topic colour. Its coloured edge and subtle tint will match the same room in the timetable and Rooms page.
- Show a compact **Online** or **Offline** tag beside the room name on each Now card. The tag stays with the room information rather than crowding the agenda list.
- On the full **Schedule**, add a two-level heading: **Online** spans all online room columns and **Offline** spans all offline room columns. Existing room columns and their colours remain directly underneath.
- Classify rooms only from the source table recorded during ingestion: Online table means Online; Offline table means Offline. The Main room follows its table. No room-name guessing.

## Verification

- Check RAN1#126bis specifically: it remains five merged rooms, the Yeongju room merges remain intact, and every room is in the correct group.
- Check the Now page at phone width: simultaneous sessions have distinct room colours, mode tags fit beside room names, and text does not overlap.
- Check the grouped Schedule heading at phone and desktop widths, including sticky behavior, horizontal scrolling, parallel lanes, filters, and opening a session.
- Run the relevant checks and confirm the preview has no errors.

## Technical details

- Add one shared room-mode helper in `src/lib/rooms.ts`, derived from `chairLaneId`.
- Add an opt-in room-colour and room-mode presentation to `SessionCard`; enable it only for **Happening now** and **Starting next**.
- Give `Timetable` a two-level sticky header. Group widths will be calculated from the existing room widths, including rooms with parallel lanes.
- Preserve topic colouring on other SessionCard uses and do not append Online/Offline to every room name across the app.

## Separate follow-up plans

After this plan is complete, present these separately, one at a time:

1. Drafts: combine venue and MEETINGS_SYNC during meeting week and remove stale archive-only entries.
2. Schedule ingestion: prefer the official RAN1#126bis v00 schedule over the draft v03 once official files exist.
3. My agenda: leaf-only selection plus explicit `10.4.x` matching to selected children such as 10.4.1 and 10.4.2.