# RAN2 schedule, built on the RAN1 pipeline

## What the user gets
- A **RAN1 / RAN2 switch** at the top of the app (next to the meeting picker). Picking RAN2 shows the same Schedule, Now, My agenda and room views, filled from the RAN2 schedule.
- Check-in, colleague alerts and calendar export work the same way for RAN2 rooms.
- RAN1 stays exactly as it is.

## How it fits: tab, switch or separate app?
| Option | Pros | Cons |
|---|---|---|
| Extra "RAN2" tab beside Schedule | Quick to see | Only the timetable; Now, My agenda, rooms and alerts would all need copies |
| **Working-group switch (recommended)** | Every page is reused; one installed app; colleagues in both groups see both | Each meeting gets a group label |
| Separate app (ran2.app) | Fully independent | Two apps to run and fix; double the upkeep |

The plan uses the switch. It's a small change because the app already handles more than one meeting.

## Where the schedule comes from
- Meetings Sync: `/ftp/Meetings_3GPP_SYNC/RAN2/Agenda/` (currently `R2_136_Schedule_v00` to `v07.docx`).
- Archive: `/ftp/RAN/RAN2/Agenda/`.
- The date rule is the same as RAN1: before the meeting, only the archive; on meeting days, only Meetings Sync; on the day after, both. Only files whose name matches the meeting number (for example `R2_136`) count, so last meeting's files never show up.
- The newest version wins (v07 over v06). The rule from RAN1 where an official file beats a Draft still applies.

## Steps
1. **Look at the RAN2 file first.** Download `R2_136_Schedule_v07.docx` and see how it lays out rooms (colours or column headings), times, breaks and agenda codes. Write down where it differs from RAN1.
2. **Add the group to meetings.** Each meeting gets a working group (RAN1 or RAN2) and its own folders and file-name pattern. Add RAN2#136 as the first RAN2 meeting.
3. **Reuse the schedule reader.** Run the same reading, merging, checks, gap and overlap safeguards and change history on RAN2 files. RAN1-only settings (main-grid wording, chair file names, "RAN1 BrkN" labels) become per-group settings. A new rule is only added if step 1 shows the RAN2 layout needs one.
4. **Agenda titles.** Take agenda item names from the RAN2 agenda document in the same folder, so "My agenda" and topic-only blocks work.
5. **Automatic updates.** The same GitHub job and five-minute watcher also check the RAN2 folder and publish RAN2 data separately. A RAN2 failure never holds up RAN1.
6. **In the app.** Add the switch and remember the choice on each device. Room labels show "(RAN2 BrkN)". Check-ins stay tied to their meeting.
7. **Check it.** Add tests using cells from the real RAN2 file, do a full rebuild and health check, and compare the Schedule page against the DOCX in the browser.
8. **Docs.** Update How to Use, the project notes and the meeting-refresh skill.

## Out of scope for now
- RAN2 Drafts (the Inbox draft folders). This can be a follow-up plan if you want it.

## Technical details
- `ingestion/meeting_discovery.py`, `remote_ftp.py` and `schedule_discovery.py`: per-group roots and filename regex (`R2_<n>(bis)?_Schedule_v<nn>`).
- `ingestion/live.py` and `room_resolver.py`: move the main-grid and Main-session markers into a group config.
- Data goes in `public/data/meetings/ran2-<n>/`; meeting slugs carry the group prefix.
- `src/types/meeting.ts`: add `workingGroup`. Meeting picker and `src/lib/rooms.ts`: label prefix by group.
- `.github/workflows/update-schedule.yml` and `/api/public/jobs/schedule-watch`: loop over groups.
