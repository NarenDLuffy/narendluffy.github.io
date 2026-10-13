# Simple source rule + table sanity checks

## 1. Where documents come from (what happens today)

| | Before meeting week | During meeting week |
|---|---|---|
| Drafts (today) | Meeting folder only | Meetings Sync, checked against the meeting-folder copy (files no longer on Sync are hidden) |
| Timetable (today) | Meeting folder + Meetings Sync (only files named for this meeting) | Meeting folder + Meetings Sync + remote FTP; newest version wins |
| 10.10.10.10 (https) | not used | Read by the phone/laptop itself when it is on the meeting Wi-Fi. GitHub cannot reach it |

So: **not quite what you described.** The timetable still reads the meeting folder during the week, and reads Meetings Sync before the week.

### Change: one rule for both drafts and timetable
- **Before the week:** read the meeting folder only.
- **During the week (the meeting days themselves; on the day before and the day after, read Meetings Sync and the meeting folder together, newest version wins):** read Meetings Sync only, plus 10.10.10.10 over https when the device can reach it. The newest version wins.
- The remote FTP stays as the night-time copy of 10.10.10.10 (same files, reachable from outside the venue). Say if you want it removed.
- If Meetings Sync can't be reached during the week, keep the last good copy and flag it in Verify data. Don't fall back to the meeting folder.
- Update the How to Use page and the meeting-week skill to match.

## 2. Not copying text from the wrong cell

Comparing pictures of the tables would be slow, would cost an AI call per file, and could still misread small text. There's a better option: checks that catch exactly the mistake we just had, run on every update.

1. **One cell, one room.** Every block remembers the exact table cell it came from. If the same cell text ends up in two rooms, the update is refused.
2. **Same item in two rooms at once.** For example, "Modulation 10.3.2" in Tamna and Yeongju A at 18:00. Refused unless the document itself lists it in both rooms.
3. **Minutes must add up.** The listed minutes in a cell must equal the slot length. This is already in place and is how the Sensing "(6)" was caught.
4. **No gaps.** Already in place.
5. **Files must agree.** When the official grid and a chair's own table cover the same room and time with different items, it shows as a conflict on the Ingestion status page.
6. **A picture only when something fails.** The failing table is turned into an image and attached to the failed GitHub run, so the cause can be seen at a glance. This is for checking by eye, not for deciding what goes in the timetable.

Each check gets a test built from the real Wednesday 14 Oct table.

## Technical details
- `ingestion/live.py discover_sources`: decide on `in_meeting_week(start, end)` (the same ±1 day rule the drafts use). Inside the week: SYNC_ROOT (+ remote FTP), name-matched. Outside the week: `walk_documents(folder_url)` only.
- `draft_tracker/update_drafts.py`: inside the week, read the Sync tree as the only source instead of merging it with the archive. Hide-don't-delete stays for files that disappear from Sync. Before the week: archive only.
- Add `cellRef` (file, table index, row, column) to the provenance of each parsed Session. A validator check rejects a single `cellRef` mapped to more than one roomId, and rejects the same agendaItems in different rooms with overlapping times unless both come from distinct cells.
- On a validation failure, `run_libreoffice.py` converts the file to PDF, `pdftoppm` renders the page, and the image is uploaded with `actions/upload-artifact@v4` (upload-artifact v5 if it exists).
