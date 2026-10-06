# Merge the duplicate Main session column

## Confirmed issue

For RAN1#126bis, **Online Session (RAN1 Main)** and **Online Session 1** are generated as separate rooms even though they represent the same white Main-chair lane. Each genuinely different coloured lane must remain separate because it belongs to a different chair.

## Changes

1. **Treat colour as chair-lane identity**
   - Read the source document’s lane/cell background colour.
   - Identify the white lane as the Main chair’s `RAN1 Main` session, even when a temporary heading says `Online Session` or `Online Session 1`.
   - Treat grey and orange lanes as separate vice-chair online sessions.

2. **Merge duplicate Main aliases automatically**
   - Merge `Online Session`, `Online Session 1`, and `RAN1 Main` only when document position, white colour, and schedule content show they are duplicate readings of the same source lane.
   - Keep the richest schedule details and source references.
   - Never merge grey or orange vice-chair lanes merely because their timing or agenda content matches Main.

3. **Preserve the chair schedule’s visual meaning**
   - Main chair: white/neutral column treatment.
   - Vice chairs: retain the grey and orange lane colours found in the latest schedule document.
   - Carry this classification into the Timetable and Rooms views instead of assigning colours only by column order.

4. **Keep future meetings automatic**
   - Base recognition on document colour plus matching schedule content, not meeting-specific room names.
   - When hotel room names are later published, keep the real room name and show `(RAN1 Main)` or the relevant breakout label in brackets.

5. **Verify the generated result**
   - Rebuild RAN1#126bis and confirm the duplicate Main/Online 1 column is gone.
   - Confirm distinct grey and orange chair-led sessions remain separate.
   - Check Timetable, Rooms, agenda filtering, session details, refresh, and calendar export against the merged room IDs.

## Technical details

The ingestion model will retain chair-lane identity, semantic role, and source colour for each room. Duplicate detection will use source-table position and colour as primary evidence, with schedule signatures and explicit `RAN1 Main` labels as supporting evidence. The frontend will map these roles to theme-safe colours while preserving the document’s white, grey, and orange distinction.
