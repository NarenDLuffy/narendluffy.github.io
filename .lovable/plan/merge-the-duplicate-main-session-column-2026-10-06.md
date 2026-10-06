# Merge the duplicate Main session column

## Confirmed issue

For RAN1#126bis, **Online Session (RAN1 Main)** and **Online Session 1** are generated as separate rooms even though they represent the same chair lane. Each genuinely different coloured lane must remain separate because one colour consistently represents one chair across both online and offline sessions.

## Changes

1. **Treat colour as chair-lane identity**
   - Read the source document’s lane/cell background colour.
   - Build one canonical column for each colour/chair across both online and offline rows.
   - Do not hard-code white as Main. Identify the Main chair’s lane from explicit schedule evidence such as the lane containing “Main session or RAN1 #number commences”, then use colour to associate that chair’s other sessions.
   - Keep every other colour as a separate vice-chair lane, even when two chairs discuss the same agenda item at the same time.

2. **Merge duplicate Main aliases automatically**
   - Merge `Online Session`, `Online Session 1`, and `RAN1 Main` only when colour/chair identity, document position, and Main-commencement evidence show they are duplicate readings of the same source lane.
   - Keep the richest schedule details and source references.
   - Never merge two different colour/chair lanes merely because their timing or agenda content matches.

3. **Preserve the chair schedule’s visual meaning**
   - Keep the source document’s colour for each canonical chair column.
   - Mark whichever canonical lane contains the explicit Main-session commencement as `RAN1 Main`.
   - Carry this classification into the Timetable and Rooms views instead of assigning colours only by column order.

4. **Keep future meetings automatic**
   - Base recognition on document colour, chair identity, table position, and explicit Main-session text—not meeting-specific room names or an assumption that Main is always white.
   - When hotel room names are later published, keep the real room name and show `(RAN1 Main)` or the relevant breakout label in brackets.

5. **Verify the generated result**
   - Rebuild RAN1#126bis and confirm the duplicate Main/Online 1 column is gone.
   - Confirm each distinct colour/chair remains a separate column across online and offline sessions.
   - Check Timetable, Rooms, agenda filtering, session details, refresh, and calendar export against the merged room IDs.

## Technical details

The ingestion model will retain chair-lane identity, semantic role, and source colour. A canonical lane will be keyed primarily by the source colour/chair relationship across online and offline sessions. Explicit commencement text determines which lane is Main; source-table position and schedule signatures resolve duplicate readings. The frontend will preserve the source colour distinction using accessible theme-safe equivalents.
