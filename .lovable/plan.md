# Schedule source transparency and Word-change accuracy

## Goal
Make the Schedule page clearly state which schedule documents actually produced the displayed timetable, and correctly apply detailed and revised content from the latest valid DOCX versions.

## Confirmed findings
- The current RAN1#126bis bundle includes and parses `Draft RAN1#126b online and offline schedules - v03.docx`; latest-revision selection already prefers v03 over v00–v02.
- The Schedule page currently lists every discovered document at the bottom, so the schedule-producing versions are not easy to distinguish from unrelated files.
- Tuesday Online Session 3 is reduced to one `10.5.4` block because the parser treats the parent `10.5.4 (120)` line as the first timed child. It then consumes the full slot before reaching `10.5.4.1`–`.4`.
- The DOCX reader currently includes struck-through runs as active text. Highlighted text is active schedule content and must remain; Word deletions and struck-through or hidden runs must not appear.
- The current RAN1#126bis bundle has no Hiroki or Sorour source. The sync mirror files found for them are labelled RAN1#126 rather than RAN1#126bis, so the existing meeting-number/bis safety rule correctly excludes them. The page must not claim an unused version.

## Changes
1. **Add a clear “Schedule based on” summary**
   - Place it near the top of the Schedule tab, below refresh controls.
   - Derive it from source IDs referenced by the canonical sessions, not from every discovered file.
   - Show each exact filename once, including the main, Hiroki, and Sorour versions whenever those valid documents actually contributed.
   - Keep the full technical source list below for deeper inspection, but distinguish “used in this schedule” from merely discovered documents.

2. **Fix parent/child agenda splitting**
   - When a timed parent line such as `10.5.4 (120)` is followed by timed descendants such as `10.5.4.1`–`.4`, treat the parent as the container and publish only the child sequence.
   - Preserve the document order and durations, clipping or reconciling totals safely against the containing timetable block.
   - Keep the existing rule that no children are invented from the agenda tree when the DOCX does not provide them.

3. **Respect Word revisions and formatting**
   - Extract active text from normal and inserted runs.
   - Exclude struck-through, double-struck, hidden, and deleted text before schedule parsing.
   - Continue parsing highlighted text as active content; highlighting is emphasis, not deletion.
   - Apply the same active-text rules in both schedule parsers and document classification so stale text cannot influence either source selection or canonical blocks.

4. **Automatic latest-version behavior**
   - Retain automatic numeric revision ranking, including compound versions such as `v08_1`.
   - Retain strict meeting-number and bis matching so the previous meeting’s personal schedules cannot leak into the current meeting.
   - If a valid current-meeting Hiroki or Sorour document appears, the next automated refresh should select it and show its exact filename without an app republish.

## Verification
- Add parser tests covering a parent `10.5.4` container with four highlighted children and verify four canonical blocks in document order.
- Add DOCX-format tests proving struck-through/deleted text is absent while highlighted/inserted text remains.
- Rebuild RAN1#126bis and verify Tuesday Online Session 3 shows `10.5.4.1`, `.2`, `.3`, and `.4` with their durations.
- Verify the affected Wednesday 17:00 block contains only active v03 content.
- Verify “Schedule based on” shows v03 and only documents that contributed to the displayed canonical schedule.
- Verify the preview and current build diagnostics are clean before publishing the corrected data.

## Technical details
- Update the shared DOCX text extraction used by `block_schedule.py`, `docx_schedule.py`, and schedule inspection.
- Update source presentation in `SourcePanel.tsx` using canonical session provenance already present in `Session.sources`.
- Record the active-run extraction rule in the project architecture notes because all future DOCX schedule ingestion must follow it.
