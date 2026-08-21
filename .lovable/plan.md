# RAN1 Live — automatic meeting discovery, archive and simple room presence

Goal: deploy once, and every future RAN1 meeting (127, 128, bis, ad-hoc) appears automatically — no code change, no hard-coded meeting number, rooms, agenda items or chair names.

## What the reference project gives us

Studied `karlla1220/3GPPSchedule`. Worth reusing:

- Directory listings on the public 3GPP site are plain HTML tables, so folders and files can be enumerated and their upload timestamps read.
- Two source locations matter: the RAN1 Inbox (chair notes + per-sub-chair folders, live during the week) and the per-meeting folder (agenda, stable documents).
- Revision picking from trailing markers like `v09` / `v04_3`, plus a "preferred meeting" lock so a briefly incomplete listing never rolls the app back to an older meeting.
- Two-stage CI: a cheap "did anything change?" check gates the expensive parse/publish job.
- Per-slot caching so only the changed part of a schedule is reprocessed.

Where we deliberately differ: the reference tool is built around one current meeting and classifies documents by folder/person name. RAN1 Live keeps a meeting registry with an archive, classifies documents by content as well as filename, keeps full source provenance per session, and never depends on who the chairs are.

## 1. Generic meeting model

- `Meeting` with stable internal `id`, URL slug, display `name`, optional number, `type` (regular / bis / adhoc / other), dates, timezone, venue, city, country, status.
- Status (upcoming / active / completed) is always calculated from dates in the meeting timezone, with an optional administrator override.
- Rooms, agenda items, sessions, sources and changes are all keyed by meeting id.
- Remove every RAN1#126 assumption from the app: the bundled demo data is deleted and replaced by generated per-meeting data files.

## 2. Current meeting selection and archive

- Home page automatically shows: meeting in progress → else nearest upcoming → else most recently completed.
- Meeting picker in the header; archive routes `/meetings`, `/meetings/ran1-126`, `/meetings/127-bis` etc.
- Completed meetings keep their final schedule snapshot, readable even after the 3GPP source changes.
- Before a meeting starts the app shows "Starts in N days" and either "Schedule not yet published" or the first published version, so people can build My Agenda in advance.

## 3. Discovery and ingestion pipeline (Python, runs in GitHub Actions)

Separate modules so a change to the 3GPP site layout never touches the parser:

- Meeting discovery: find RAN1 meetings, dates, venue, timezone and their folders; create new meetings automatically.
- Source discovery: enumerate Inbox / chair-notes / meeting folders, find candidate schedule documents.
- Classifier: decide what each document is (main, chair, sub-chair, detailed, online/offline, room, venue, unknown) from filename *and* content — day tables, agenda-item patterns, room names — never from a person's name.
- Revision selection: filename revision markers, server timestamps and content hash together. A newer file only replaces the current schedule after it parses and validates.
- DOCX parser: deterministic table extraction (merged cells, day/time/room grid, agenda patterns) first; ambiguous blocks flagged for review rather than invented.
- Merger: main schedule for structure, rooms, blocks and breaks; detailed/sub-chair documents for agenda items, ordering, finer timing and session leads. Conflicts are recorded, never silently dropped.
- Validator: time sanity, dates within the meeting, known rooms, plausible agenda codes, non-empty schedule, correct meeting identity. On failure the previous good schedule keeps being served and the UI shows "Schedule update delayed — last successful update HH:MM".
- Change detector: produces the Changes feed by diffing against the last published snapshot.
- State store: source hashes, revisions and per-slot hashes so unchanged material is never reprocessed.

Output: `public/data/meetings.json` plus one folder per meeting with `meeting / schedule / rooms / agenda / sources / changes` JSON. The frontend never touches a Word document.

## 4. Provenance

Every session records which document and revision contributed which fields. The schedule view shows "Updated 14:37" and an expandable "Sources: Main v07 · Detailed v07.1", and whether data came from the public 3GPP site or a meeting-local source.

## 5. GitHub Actions

- `discover-meetings.yml` — meeting registry refresh, low frequency.
- `update-schedule.yml` — event-aware: roughly every 5 minutes during an active meeting, every few hours in the days before, once or twice a day between meetings. Cheap change-check gates the full run. Cadence values live in one config file.
- `deploy-pages.yml` — build and publish.

## 6. Meeting-local (10.10.10.10) source

Kept as a separate, optional ingestion path behind an interface, because browsers and GitHub Actions both may be unable to reach it. First version only reports "meeting-local source available / unavailable" and, when reachable and genuinely newer by revision + hash + successful parse, offers it as the display source. Being unreachable is normal and never shown as an error.

## 7. Company room presence — no accounts

Per your answer, no sign-in at all:

- A company group is a shared link/code (e.g. `/company?g=<code>`). Opening it once joins this device to that group; you type a display name that stays on the device.
- Check into a room with one tap, from the current meeting's discovered room list. Presence expires automatically after a couple of hours and can be cleared any time.
- Coverage view uses the current meeting's real sessions and agenda items: who is in which room, and which sessions nobody from the group is covering.
- Presence is meeting-scoped: when the meeting rolls over, presence starts empty while the group and personal agenda selections stay.
- Phase 1 works on-device only (so it is useful immediately and fully private); the storage layer sits behind one service so it can be switched to shared realtime storage later without touching the UI. Honest caveat shown in the UI: anyone holding the code can see and post presence.

## 8. Proof that it is meeting-independent

Two fixture datasets are generated and both must render with zero code changes: the real-shaped RAN1#126 (Barcelona) and a synthetic second meeting with a different number/type, different dates, different city and venue, different rooms, different document names and a different agenda tree. Rollover, archive and empty presence are demonstrated across the two.

## Technical notes

- Frontend: new `src/types/meeting.ts`, reworked `src/types/schedule.ts`, services split into `meetingService.ts` / `scheduleService.ts` / `presenceService.ts` / `localSource.ts`; all routes read the selected meeting from one hook. This type migration is already in progress and currently leaves build errors in `AppShell`, `Timetable`, `SourcePanel`, `ics.ts` and the routes — finishing it is step 1.
- New routes: `/meetings`, `/meetings/$slug`, `/admin` (review queue for unclassified documents and conflicting revisions, with approve / reclassify / ignore).
- Ingestion: `ingestion/{meeting_discovery,source_discovery,downloader,classifier,docx_parser,merger,validator,change_detector,state,generate,config}.py` plus a fixture generator for the two test meetings.
- Data lives in `public/data/`, one directory per meeting, as described above.
