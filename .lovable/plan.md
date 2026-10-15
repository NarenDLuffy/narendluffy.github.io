# Fix the Drafts page waiting forever, and accept the jeju_icc host

## What is wrong (checked in the code)
1. **"No draft folder has been published" + endless "Checking…"**: the saved drafts copy is there (2,094 files, from 21:54 UTC). But the page shows nothing until the live check finishes. During the meeting week that check opens every folder in Meetings Sync (about 205 folders, one after another) and tries 10.10.10.10 first. Until it's done, the page acts as if there's no data and shows the "nothing published yet" message.
2. **FTP host refused**: the address check only allows letters, digits and hyphens, so the underscore in `jeju_icc.3gpp.org` gets rejected. Real FTP host names can contain underscores.

## Changes
1. **Saved copy first, live check after**: the page shows the saved drafts right away. The live Meetings Sync / 10.10.10.10 check runs in the background, and a small "Checking live folders…" note shows while it runs. When it finishes, the list updates in place. The "nothing published yet" message only shows when there really is no saved copy and the live check found nothing.
2. **Faster live check**: open several folders at the same time (about 6) instead of one by one. Give the 10.10.10.10 attempt a short time limit so a missing venue server can't stall everything.
3. **Host check**: allow underscores in host names (letters, digits, `-`, `_`, separated by dots). Once you save `jeju_icc.3gpp.org`, the GitHub refresh picks it up automatically.
4. **GitHub Actions**: your message was cut off after "Also Github actions". After building, I'll check the latest health record. If you saw a specific error, please paste it.

## Technical details
- `src/services/draftService.ts`: split into a snapshot query (`loadPublishedDrafts`, renders immediately) and a live query (`probeLiveDrafts`, runs with `placeholderData` = snapshot). `useDrafts` returns snapshot index until live resolves, and `isRefreshing` follows the live query only.
- `src/routes/drafts.index.tsx`: empty-state only when both are settled and empty; inline live-check indicator.
- `src/lib/listingParser.ts` `walkListing`: bounded concurrency (6); venue candidate gets a short overall budget.
- `src/lib/meetingSettings.functions.ts` HOST_RE: `/^[a-z0-9_]([a-z0-9_-]*[a-z0-9_])?(\.[a-z0-9_]([a-z0-9_-]*[a-z0-9_])?)+$/i`. Also check that `ingestion/remote_ftp.py` doesn't reject underscores.
- Verify in the browser: Drafts shows files in under 2s; save the jeju_icc host.
