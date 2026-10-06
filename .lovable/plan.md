# RAN1 Live — update "How to use" and remove "Share this checklist"

## 1. Remove "Share this checklist" from How to use
- `src/routes/help.tsx`: delete the entire "Share this checklist" Section (lines with the Teams-message and full-checklist links). The checklist files themselves stay in `public/` and `docs/` — only the Help-page section is removed.
- `docs/HOW-TO-USE.md` and `public/COLLEAGUE-CHECKLIST.md`: remove the references to the Help page's "Share this checklist" link so the docs stay consistent with the page.

## 2. Bring How to use up to date with the latest changes
Update `src/routes/help.tsx` (and mirror the same content in `docs/HOW-TO-USE.md`) so it describes what the app does today:

- **Schedule / Timetable**: room colours (each room has its own colour on the timetable, the Rooms tab and room pages); "(RAN1 Main)" style session labels in brackets after the room name where the chairs' documents give them; the agenda filter dims (or hides, via "Hide others") non-matching blocks; a Refresh button showing when the schedule was last rebuilt.
- **Tap a block**: shows the full agenda titles (e.g. "10.5.5 — Other physical channels and signals") with the per-item time breakdown, plus the room's session label.
- **My agenda / ICS export**: exported times use the meeting city's time zone (with daylight-saving handled); events include room with label, full agenda names, and 30-minute reminders for FL deadlines.
- **FL deadlines**: manually add a deadline per agenda item ("Deadline" button on agenda items in the details sheet); reminders appear as a badge on Now and as calendar alarms in the export. Note that the RAN1 email reflector is members-only, so deadlines are not detected automatically.
- **Now**: shows a Refresh button and deadline badges too.
- **Rooms**: only the current meeting's rooms; each with its colour and session label.
- **Venue mode section**: shorten to a note that venue mode is currently switched off and the app uses the public 3GPP meeting-sync source; the on-venue-Wi-Fi instructions and cache-clearing details stay available in the help text only as a short note (plumbing kept for the future).

## 3. Room and session names updating automatically (no code change)
Confirm and explain: rooms and session labels (e.g. "Offline Session 1" gaining the hotel room's real name, "(RAN1 Main)" on the official session) come from the latest schedule documents. The background job rebuilds the schedule from the newest 3GPP documents every 5 minutes during meeting hours, so when the chairs upload named rooms/sub-chair plans, they appear on the Rooms tab, Timetable and room pages automatically — no republish needed (data loads live from the updated copy). If a room name never appears in the documents, it cannot be shown; a Refresh can be tapped to pull the newest data immediately.

## Technical details
- Only presentation/doc files change: `src/routes/help.tsx`, `docs/HOW-TO-USE.md`, `public/COLLEAGUE-CHECKLIST.md` (drop the "Share this checklist" cross-reference). No ingestion or backend changes.
- Verify the /help page renders without the checklist section and the new sections appear, via a browser check of the preview.
