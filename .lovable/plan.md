# Colleague Testing Checklist for RAN1 Live

## Goal
Create a single, shareable markdown checklist that colleagues can use to walk through every feature of the published app and report back with feedback, bugs, and upgrade ideas.

## Deliverable
A new file `docs/COLLEAGUE-CHECKLIST.md` plus a short in-app link from `/help` so users can reopen it.

## Checklist structure

### 1. Before you start
- Open the site on the device you will use during the meeting (phone is best).
- Add it to your home screen / install as PWA.
- Note your browser and OS.

### 2. Meeting discovery & switcher
- Confirm the current meeting is auto-selected.
- Tap the header and switch to a different meeting.
- Confirm the schedule, drafts, and rooms update to that meeting.
- Switch back.

### 3. Now page
- Verify the meeting-local clock matches the header.
- Confirm "Happening now" shows sessions that are currently running.
- Confirm "Starting next" shows upcoming sessions.
- Tap a session and check the agenda-item breakdown.

### 4. Schedule / Timetable
- Confirm the grid shows 08:30–19:30 for every day.
- Check that parallel tracks and shared rooms are clear.
- Use search and filters.
- Star a session and confirm it appears in My agenda.
- Tap a block and verify the timed sub-slots look correct.

### 5. My agenda
- Confirm starred sessions are listed in time order.
- Export `.ics` and try importing it into your calendar app.
- Remove a star and confirm it disappears.

### 6. Drafts
- Confirm the source line (Venue / Sync / Published).
- Press "Refresh now" and note the status message.
- Toggle between "My items" and "All agenda items".
- Follow an agenda item and confirm it moves into "My items".
- Open a folder and verify the breadcrumb hierarchy looks right.
- Mark all read and confirm unread badges clear.

### 7. Rooms
- Confirm every room in use is listed.
- Tap a room and verify its day schedule.

### 8. Company presence
- Set a group code and display name.
- Check in to a room.
- Ask a colleague to do the same and confirm you see each other.
- Confirm presence expires after two hours.

### 9. Changes
- Open the Changes page and verify any schedule diffs are understandable.

### 10. Offline / resilience
- Turn off Wi-Fi (or use airplane mode) and reload the last-opened page.
- Confirm the stale/cached banner appears.
- Turn Wi-Fi back on and confirm fresh data returns.

### 11. Help & admin
- Open `/help` and confirm the guide makes sense.
- Open `/admin` and verify ingestion status is readable.

## Feedback prompts
For each section, ask:
- Did anything not work as expected? (screenshot + steps)
- Was anything confusing the first time?
- What feature would you use most during the week?
- What is missing that you would want before RAN1#126?
- Any data errors (wrong time, wrong room, missing session, duplicate session)?

## Implementation steps
1. Write `docs/COLLEAGUE-CHECKLIST.md` with the sections above, formatted as checkboxes.
2. Add a link in `src/routes/help.tsx` under a new "Share this checklist" section.
3. Do not change app behavior or data pipeline.

## Success criteria
- The file is readable on GitHub and can be copy-pasted into an email/Slack.
- The checklist covers every route and major interaction currently in the app.
- `/help` points to the checklist.
