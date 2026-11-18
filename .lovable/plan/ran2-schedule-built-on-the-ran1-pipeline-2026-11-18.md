# RAN2 schedule, built on the RAN1 pipeline

## What the user gets
- A **RAN1 / RAN2 switch** at the top of the app (next to the meeting picker), chosen by you. Picking RAN2 changes the whole app: Schedule, Now, My agenda, Rooms, Drafts, check-in and alerts all show RAN2.
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
- RAN2 has **one schedule file per meeting** (no extra chair files). Meetings Sync: `/ftp/Meetings_3GPP_SYNC/RAN2/Agenda/` (currently `R2_136_Schedule_v00` to `v07.docx`).
- Archive: `/ftp/RAN/RAN2/Agenda/`.
- The date rule is the same as RAN1: before the meeting, only the archive; on meeting days, only Meetings Sync; on the day after, both. Only files whose name matches the meeting number (for example `R2_136`) count, so last meeting's files never show up.
- The newest version wins (v07 over v06). Since there's only one file, the merging of several chair files is skipped, but the checks for gaps, overlaps, crossed-out text and changes from the last version still run. The rule from RAN1 where an official file beats a Draft still applies.

## Steps
1. **Look at the RAN2 file first.** Download `R2_136_Schedule_v07.docx` and see how it lays out rooms (colours or column headings), times, breaks and agenda codes. Write down where it differs from RAN1.
2. **Add the group to meetings.** Each meeting gets a working group (RAN1 or RAN2) and its own folders and file-name pattern. Add RAN2#136 as the first RAN2 meeting.
3. **Reuse the schedule reader.** Run the same reading, merging, checks, gap and overlap safeguards and change history on RAN2 files. RAN1-only settings (main-grid wording, chair file names, "RAN1 BrkN" labels) become per-group settings. A new rule is only added if step 1 shows the RAN2 layout needs one.
4. **Agenda titles.** Take agenda item names from the RAN2 agenda document in the same folder, so "My agenda" and topic-only blocks work.
5. **Automatic updates.** The same GitHub job and five-minute watcher also check the RAN2 folder and publish RAN2 data separately. A RAN2 failure never holds up RAN1.
6. **In the app.** Add the switch and remember the choice on each device. Every page reads the selected group: Schedule, Now, My agenda, Rooms, Drafts and the Help page. Room labels show "(RAN2 BrkN)".
7. **Check it.** Add tests using cells from the real RAN2 file, do a full rebuild and health check, and compare the Schedule page against the DOCX in the browser.
8. **Docs.** Update How to Use, the project notes and the meeting-refresh skill.

## Drafts and rooms for RAN2
- **Drafts:** they're read from RAN2's Inbox, either the meeting's own folder `/ftp/tsg_ran/WG2_RL2/TSGR2_<n>/Inbox/` or Meetings Sync `/ftp/Meetings_3GPP_SYNC/RAN2/Inbox/`. The same date rule, crawl, hide-don't-delete rule and per-meeting FTP host apply. Folders are grouped by RAN2 agenda item.
- **Rooms:** RAN2 rooms are taken from its schedule file. They're separate from RAN1 rooms, even when the name is the same, so a check-in in RAN1 never shows someone in a RAN2 room.
- **Check-in and alerts:** they belong to the selected group's meeting. Colleague alerts only reach people looking at the same group.
- **Company codes** work in both groups.

## Technical details
- `ingestion/meeting_discovery.py`, `remote_ftp.py` and `schedule_discovery.py`: per-group roots and filename regex (`R2_<n>(bis)?_Schedule_v<nn>`).
- `ingestion/live.py` and `room_resolver.py`: move the main-grid and Main-session markers into a group config.
- Data goes in `public/data/meetings/ran2-<n>/`; meeting slugs carry the group prefix.
- `src/types/meeting.ts`: add `workingGroup`. Meeting picker and `src/lib/rooms.ts`: label prefix by group.
- Drafts: `src/lib/drafts.functions.ts`, `syncCrawl.server.ts`, `draftLiveSource.ts` and the drafts workflow take a per-group Inbox root. Presence and alerts are scoped by meeting slug (already the case; check that the push topics are too).
- `.github/workflows/update-schedule.yml` and `/api/public/jobs/schedule-watch`: loop over groups.
