# Fix the Drafts page waiting forever, and accept the jeju_icc host

## What is wrong (checked in the code)
1. **"No draft folder has been published" + endless "Checking…"**: the saved drafts copy is there (2,094 files, from 21:54 UTC). But the page shows nothing until the live check finishes. During the meeting week that check opens every folder in Meetings Sync (about 205 folders, one after another) and tries 10.10.10.10 first. Until it's done, the page acts as if there's no data and shows the "nothing published yet" message.
2. **FTP host refused**: the address check only allows letters, digits and hyphens, so the underscore in `jeju_icc.3gpp.org` gets rejected. Real FTP host names can contain underscores.

## Changes
1. **Saved copy first, live check after**: the page shows the saved drafts right away. The live Meetings Sync / 10.10.10.10 check runs in the background, and a small "Checking live folders…" note shows while it runs. When it finishes, the list updates in place. The "nothing published yet" message only shows when there really is no saved copy and the live check found nothing.
2. **Faster live check**: open several folders at the same time (about 6) instead of one by one. Give the 10.10.10.10 attempt a short time limit so a missing venue server can't stall everything.
3. **Host check**: allow underscores in host names (letters, digits, `-`, `_`, separated by dots). Once you save `jeju_icc.3gpp.org`, the GitHub refresh picks it up automatically.
4. **GitHub Actions / timetable stuck since last night (causes the Friday 10.5.1 order)**: the published timetable was last updated at 22:48 UTC yesterday and still uses the main schedule **v02**. The chair has since uploaded **v03 and v04** to Meetings Sync. v04 has the new order and timings (e.g. 10.5.1.3 → 10.5.1.2 → 10.5.1.1). So the parsing is fine, but no update has gone out for about 10 hours. Either the GitHub updater has stopped, or each new run is refused by the safety checks (a refused run keeps the old timetable online).
   - Rebuild RAN1#126bis locally from v04. If a safety check refuses it, find the general cause (schedule audit skill), fix the rule and add a test, never loosen the check. Then publish the corrected timetable.
   - Confirm Friday matches v04 (order and minutes for 10.5.1.x) in the browser.
   - Make a stuck timetable visible: the Schedule page shows "Newer schedule file found but not yet used (v04)" when a newer chair file exists than the one shown. Then neither of us has to spot it by eye.
   - Check the latest GitHub run results. If you see a red run, please paste its error.

## Technical details
- `src/services/draftService.ts`: split into a snapshot query (`loadPublishedDrafts`, renders immediately) and a live query (`probeLiveDrafts`, runs with `placeholderData` = snapshot). `useDrafts` returns snapshot index until live resolves, and `isRefreshing` follows the live query only.
- `src/routes/drafts.index.tsx`: empty-state only when both are settled and empty; inline live-check indicator.
- `src/lib/listingParser.ts` `walkListing`: bounded concurrency (6); venue candidate gets a short overall budget.
- `src/lib/meetingSettings.functions.ts` HOST_RE: `/^[a-z0-9_]([a-z0-9_-]*[a-z0-9_])?(\.[a-z0-9_]([a-z0-9_-]*[a-z0-9_])?)+$/i`. Also check that `ingestion/remote_ftp.py` doesn't reject underscores.
- Verify in the browser: Drafts shows files in under 2s; save the jeju_icc host.
