# Merge the duplicate Main session column

## Confirmed issue

For RAN1#126bis, **Online Session (RAN1 Main)** and **Online Session 1** are generated as separate rooms, but their timed agenda blocks are duplicates from the same source document. They should not be two timetable columns.

## Changes

1. **Treat the white schedule lane as the official Main session**
   - Read the source document’s lane/cell background colour.
   - Identify the white lane as `RAN1 Main`, even when its temporary heading says `Online Session` or `Online Session 1`.

2. **Merge duplicate Main aliases automatically**
   - Merge `Online Session`, `Online Session 1`, and `RAN1 Main` only when their week-long timing and agenda content show they are the same lane.
   - Keep the richest schedule details and source references.
   - Do not merge genuinely different parallel sessions.

3. **Preserve the chair schedule’s visual meaning**
   - Main session: white/neutral column treatment.
   - Other chairs’ online sessions: use the grey and orange lane colours found in the latest schedule document.
   - Carry this classification into the Timetable and Rooms views instead of assigning colours only by column order.

4. **Keep future meetings automatic**
   - Base recognition on document colour plus matching schedule content, not meeting-specific room names.
   - When hotel room names are later published, keep the real room name and show `(RAN1 Main)` or the relevant breakout label in brackets.

5. **Verify the generated result**
   - Rebuild RAN1#126bis and confirm the duplicate Main/Online 1 column is gone.
   - Confirm distinct grey and orange chair-led sessions remain separate.
   - Check Timetable, Rooms, agenda filtering, session details, refresh, and calendar export against the merged room IDs.

## Technical details

The ingestion model will retain a semantic lane role and source colour for each room. Duplicate detection will use schedule signatures across the week, with colour and explicit `RAN1 Main` labels as supporting evidence. The frontend will map semantic roles to theme-safe colours while preserving the source document’s white, grey, and orange distinction.
