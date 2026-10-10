# Drafts: stop showing the previous meeting's files from Meetings Sync

## What is happening

- The scheduled GitHub job already does the right thing: it reads the Meetings Sync folder for drafts only while a meeting is `active` (meeting week). Before the week it uses the meeting's own folder (`TSGR1_126b`).
- The in-app live check does NOT have that guard. On every refresh it crawls Meetings Sync and merges whatever is there. Right now that folder still holds RAN1#126 files, so they appear under RAN1#126bis — that is the second "10.8.2 (Aspects of integration) · 59 files" row in your screenshot.
- The sync folder's subfolders (e.g. `10.8.2 ...`) carry no meeting number, so the files can't be told apart by name — the reliable check is timing.

## Fix

1. **Meeting-week gate in the live check** (`src/services/draftLiveSource.ts`): the venue server and Meetings Sync are only probed when the selected meeting is in its meeting week (status `active`, or today within start–end date in the meeting's timezone, with one day of slack either side). Outside that window the app shows only the published snapshot built from the meeting's own folder.
2. **Extra sanity check by date**: even during the week, ignore any Meetings Sync file whose modified time is older than ~14 days before the meeting start — catches leftovers from the previous meeting if the folder isn't cleared on time.
3. **Clean the current view**: files already pulled in come only from the in-page merge (not saved anywhere), so after the fix the duplicate 59-file row disappears on the next load; the "59 new files" notice resets with it.
4. Record the rule in project notes: live Meetings Sync/venue drafts belong to a meeting only during its week.

## About the blue Publish button

It turned blue because the planning notes file changed, which counts as an unpublished change. Publishing this fix will clear it.
