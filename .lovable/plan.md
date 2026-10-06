# RAN1 Live — rooms, agenda names, filters, colours, FL reminders

## 1. Rooms tab shows only the current meeting's rooms
Today the RAN1#126bis room list still contains last meeting's rooms (Praetorium, 1.1 Himalaya, 0.4 Brussels) plus junk names like "b Online Session 1".
- Ingestion: a room is kept only if it appears in this meeting's latest schedule documents (chair grid / sub-chair plans). Rooms coming from older revisions or another meeting's files are dropped.
- Clean room names (strip leading stray letters like "b ", document title fragments).
- App: Rooms tab and Timetable additionally hide any room with no sessions in the current meeting, so leftovers never show even in stale data.

## 2. Session label in brackets after the room
- Ingestion reads the session label the chair uses for each room (RAN1 Main, RAN1_Brk#1, RAN1_Brk#2, Offline …) from the headings/grid and stores it on the room.
- Displayed as e.g. "1.1 Himalaya (RAN1 Brk2)", "Praetorium (RAN1 Main)" on Rooms, Timetable headers and session details. Rooms without a known label show just the name.

## 3. Tap a block to see agenda names
- Agenda titles taken from the latest Draft Chair Notes revision (meeting folder + sync mirror, highest version wins), falling back to the official agenda document.
- Tapping a block opens a details sheet: time, room (label), and each agenda item with its full title, e.g. "10.5.5 — Other physical channels and signals", plus the time breakdown.
- Titles also shown in the agenda filter chips (tooltip/long-press) and in the ICS export.

## 4. Remove the venue mode button, keep the plumbing
- Hide the venue banner/button and auto-hop from the app shell and Drafts page.
- Keep the venue code and the 10.10.10.10 probing behind a single off switch so it can be re-enabled if the server ever offers HTTPS. Help page text updated accordingly.

## 5. "My agenda items" filter dims the rest
- When a filter is active, all blocks stay in place; matching blocks are highlighted, non-matching ones greyed out (low opacity, no colour).
- A toggle "Hide others" lets you switch between dimmed and fully hidden. Breaks/lunch always stay visible.
- Export still exports only the matching blocks.

## 6. Colour per room
- Each room gets a stable colour from a fixed palette (by room order), used for the column header, block left border/tint and the Rooms tab dot. Works in light and dark theme; dimmed blocks lose their colour.

## 7. FL summary deadline reminders
- The RAN1 email reflector (3GPP_TSG_RAN_WG1 on list.etsi.org) is members-only behind an ETSI login, so the app cannot read it automatically.
- What is possible without the reflector:
  - Parse FL-related deadlines that chairs write in the Chair Notes / session plans (e.g. "FL summary #2 by Wed 10:00").
  - Detect when a new FL summary file appears in the Inbox for your followed agenda items (already tracked by Drafts) and flag it.
  - Let you add a deadline manually per agenda item ("FL summary #1 due Tue 18:00").
- Reminders show as an in-app badge/banner on NOW and Drafts, and as alarms in the ICS export (phone calendar notifies you). Browser push notifications are not reliable on iPhone, so calendar alarms are the main channel.

## Technical details
- `ingestion/live.py`, `canonical_schedule.py`: filter rooms to those referenced by the latest-revision sources for the meeting; add `sessionLabel` to `Room` (models.py + `src/types/schedule.ts`); name cleanup.
- New agenda-title extractor over latest Chair Notes DOCX → `agenda.json` titles (keep existing as fallback).
- `Timetable.tsx` / `SessionCard.tsx`: dim vs hide mode (`?dim=0` search param), room colour via CSS variables defined in `styles.css` (palette tokens `--room-1..8`), session detail sheet (shadcn Sheet).
- `AppShell.tsx`, `drafts.index.tsx`: remove `VenueModeBanner` render; add `VENUE_MODE_ENABLED = false` in `venueMode.ts`.
- Deadlines: parsed into `deadlines.json` per meeting; manual ones stored in localStorage; ICS `VALARM` 30 min before.
- Regenerate RAN1#126bis data after ingestion changes and verify room list in the preview.

## 8. Fix the failing GitHub "Update schedule" job
- Cause: the schedule job and the drafts job both save refreshed data to the same repo every few minutes. When the drafts job saves first, the schedule job's save is rejected ("fetch first"). It is not a 3gpplive.net problem, and the job is needed — it keeps the timetable fresh.
- Fix: the schedule job pulls the latest changes and retries the save (up to 3 times), same as the drafts job already does; both jobs share one queue so they never save at the same moment.
- Retire 3gpplive.net: stop deploying the venue copy there (it never reached 10.10.10.10 because phones force HTTPS). Venue code stays in the app, switched off, so it can be revived if the server gets HTTPS. You can then let the domain lapse or point it elsewhere.

## 9. Manual "Refresh" for the schedule
- Drafts already has "Refresh now" (checks the drafts folders live, so new FL summaries appear immediately).
- Add a "Refresh" button on Timetable, NOW and Rooms:
  - Step 1 (instant): reload the latest published schedule, bypassing the phone's saved copy.
  - Step 2: ask GitHub to rebuild the schedule from the newest 3GPP documents right away (instead of waiting for the next 5-minute run), then show "Rebuilding… updated hh:mm" when the new data lands (usually 1–3 minutes).
- Step 2 needs a GitHub connection with permission to start the update job; the button is limited to one trigger per few minutes so it cannot be spammed.
- Technical: server function calls GitHub `workflow_dispatch` for update-schedule.yml via the GitHub connector; the app polls `generatedAt` until it changes.
