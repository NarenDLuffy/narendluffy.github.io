---
name: meeting-week-refresh
description: Refresh the RAN1 Live! timetable for the meeting that is actually running and prove the published schedule is right. Use when the timetable looks stale, wrong or missing sessions, or when asked to "update the schedule/timetable".
---

# Meeting-week refresh

The timetable is built from the chairs' own Word files by `ingestion/`, committed
to the GitHub repo, and read live by the site — so a refresh needs no publish.

## Steps

1. Confirm which meeting is live and that its dates make sense:

   ```
   python3 -c "import json;m=json.load(open('public/data/meetings.json'))['meetings'];print([(x['slug'],x['status'],x['startDate'],x['endDate']) for x in m][-3:])"
   ```

   The `active` meeting is the one the app serves. Dates come from the 3GPP
   portal — never hand-edit them into the data files.

2. Rebuild only that meeting. A rebuild of every meeting times out, so always
   pass the meeting:

   ```
   python -m ingestion.generate_schedule --meeting <slug-fragment>
   ```

   e.g. `--meeting 126-bis`. It re-downloads only documents whose hash changed,
   and keeps the previous schedule if validation fails.

3. Prove it worked, in this order:
   - `node scripts/check-meeting-health.mjs --slug <slug>` — the record that run
     just wrote: sessions, rooms, sources, and anything it could not do.
   - `ingest.lastSuccessfulAt` in `public/data/meetings/<slug>/schedule.json`
     moved.
   - Room count held against the previous record. A sudden change means a room
     name stopped matching: room presentation lives in `src/lib/rooms.ts`, and
     the merge rules in `ingestion/room_resolver.py` decide when two names are
     one room.
   - The source list names the **official** file, not a `Draft …` one:

     ```
     python3 -c "import json;print([s['fileName'] for s in json.load(open('public/data/meetings/<slug>/health.json'))['schedule']['sources']])"
     ```

     An official file supersedes every Draft revision of the same family,
     whatever the version number says.

4. Guard the public bundle: `node scripts/check-public-data.mjs`.

## When something fails

- Validation errors keep the old schedule and print why. Fix the parser; never
  lower the guard to make a run pass.
- A source that vanished: the file may not be uploaded yet, or
  `_belongs_to_meeting` in `ingestion/live.py` rejected it because it names a
  different meeting. That rejection is deliberate — the previous meeting's rooms
  must never leak into the next one.
- Times are never invented: a block splits into items only when the document
  states minutes that fit.

Related: `new-meeting-setup` before the week, `drafts-live-merge-check` for the
drafts side, `publish-and-verify` when the site itself changed.
