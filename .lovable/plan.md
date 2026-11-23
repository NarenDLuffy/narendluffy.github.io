# Lighter on 3GPP, ready for many users, plus RAN4, SA1, SA2 and a drafts discussion graph

## What his project shows (karlla1220/3GPPSchedule)
- He supports RAN1–4, SA1, SA2 and RAN Plenary. He has no SA3–6 and no CT.
- **Each group publishes its schedule differently:**
  - **RAN4:** a PowerPoint (PPTX) with one slide per day. Rooms run across, times run down, and orange cells are breaks. A topic list in Excel and the agenda list (agenda.csv) sit next to it.
  - **SA1:** Word chair agendas such as "Agenda for SA1#115_Thursday_1030". The newest one is picked by the day and time in its name. Sometimes a separate "schedule" Word file takes over the timetable.
  - **SA2:** a Word "Session Plan – rN", sometimes zipped, found in Inbox/Drafts/_Session_Plan_Updates. It is a grid of quarters (Q0–Q5) × rooms per day.
- **How he keeps load low:**
  - He keeps a saved cache of every file and asks 3GPP "send it only if it changed".
  - Each folder listing is read once per run.
  - Builds run about every 20 minutes, and two builds never run at once.
- **The drafts picture (specDuck):** it is a timeline per agenda item. Each line is a discussion thread (Part 1–4, template, draft LS). Each dot is an upload, labelled with its version and company. Purple bars mark the moderator's numbered summaries (R1-26xxxxx).
- He shows no software license. I'll rebuild these readers in our own code from the public 3GPP folders, rather than copying his files. It's still worth asking him for permission or a license if you want to borrow more.

## Part A — Reduce load (do this first)
1. **One shared Drafts scan for everyone.**
   - A backend job scans each group's live Drafts tree and saves the result.
   - It runs every 2 minutes on meeting days, every 15 minutes around the meeting, and hourly otherwise. Groups without a meeting are skipped.
   - Phones read only the saved copy. If it is stale, a single refresh runs behind a lock.
2. **"Only if changed" requests.** Ask 3GPP to send a folder or file only when it has changed, like he does. Recheck busy Inbox and Round folders every time, quiet ones less often, and pause briefly between batches.
3. **Hidden tabs do nothing.** No refreshing in the background or with the screen off; refresh once when the user returns.
4. **Room presence and backup alerts are pushed** instead of every phone asking every 15–20 seconds. A slow 2-minute check stays as a backup.
5. **Background jobs follow the meeting calendar.** Full speed only during the meeting window, slow otherwise. Downloaded files are cached between runs (the Schedule job already does this for Word files; extend it to every file).
6. **Shared caching on data files** (about 60 seconds), so many users share one download.

## Part B — New working groups
For each group: add it to the group switch, schedule reader, agenda, rooms, Drafts root and health checks. RAN1–3 stay untouched. Same rules as today: never invent times, and block the publish on overlaps or gaps.
- **RAN4:** PPTX slide reader (built-in zip/XML reading, no extra library). Orange cells = breaks, struck-through text skipped. The newest file is chosen by the revision number inside the file, then the file's date. The Excel topic list and agenda.csv give the agenda codes and titles.
- **SA1:** Word agenda reader. Find the table whose first row has 3 or more weekdays. Rows without a written time take the gap between their neighbours. Rooms come from "MEETING ROOMS" and in-cell labels. Newest file by day and time in its name; a "schedule" Word file wins when present. Unpack zipped agendas.
- **SA2:** Session Plan reader for the Q0–Q5 × room grid, half-day columns, merged cells and accepted tracked changes. Newest file is the highest "rN", zipped files are unpacked. Agenda from agenda.csv.
- **Drafts for these groups:** use each group's Inbox/Drafts tree through the shared scan from Part A. Folders are linked to agenda items by their leading number, and unmatched ones are shown under "Other".
- **Later:** RAN Plenary, SA3–6 and CT, once we've looked at where each publishes its schedule.

## Part C — Drafts activity view (our own, simple design)
- On each agenda item's Drafts page, add an "Activity" view next to the current list.
- One card per discussion thread (for example "FL summary – Part 2", "Draft LS on DMRS power boosting", "Company uploads"). Each card shows the latest version, who uploaded it and when, and a "new since you last looked" dot.
- Under each card, a small horizontal timeline of its versions (v0 → v1 → v2). Tap one to open the file.
- The moderator's numbered summaries appear as clear "Summary #N" milestones across the top, so you can see what is new since the last summary.
- Built entirely from the saved scan, so it adds no load on 3GPP.

## Order
A (load) → B: RAN4 → SA2 → SA1 → C (activity view). Each step is tested against a real past meeting's files before going live.

## Technical details
- Table `drafts_live_scan` (group, meeting, result JSON, validators per folder, scanned_at, lock_until). Public read access, written only by the server. `/api/public/jobs/drafts-scan` runs on a managed 2-minute schedule and checks the meeting phase.
- Conditional requests use ETag/Last-Modified stored per URL. Ingestion gets a shared `ingestion/http_cache.py` (on-disk bytes + validators + SHA check), saved by actions/cache between runs.
- New `ingestion/groups.py` entries. New files `ran4_schedule.py` (PPTX via zipfile + lxml), `sa1_schedule.py`, `sa2_schedule.py`, and a shared `agenda_csv.py`. Tests use real cells from past meetings.
- Activity view: a thread classifier in `src/lib/draftThreads.ts`, which parses names like "FL summary #1 (Part3) … v2 vivo" and "R1-26xxxxx". Uses the existing UI parts, with no new library.
- Presence and alerts move to realtime doorbell events, replacing the setInterval polling.
