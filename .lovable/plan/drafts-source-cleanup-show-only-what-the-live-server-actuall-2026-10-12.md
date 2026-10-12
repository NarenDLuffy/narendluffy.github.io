# Drafts source cleanup: show only what the live server actually holds

## What is wrong today (confirmed in the code and the published data)

1. **Old archive files survive the live refresh.** `mergeLive` in `src/services/draftLiveSource.ts` starts from the published snapshot and only ever adds or updates — its own rule says "published artifacts absent from the live tree are kept untouched". The RAN1#126bis snapshot was built from the meeting's own folder (`draftsRootUrl = .../TSGR1_126b/Inbox/drafts/`), so its leftovers — for example the 6 files under `10.8 (isac)/10.8.1 (evaluations)/round 1` — keep showing during the meeting week even though the live server no longer lists them.
2. **The two trees are not rooted at the same place, so nothing ever matches.** The live probe crawls `.../RAN1/Inbox/` and records paths like `drafts/10.8 (isac)/10.8.1 (evaluations)/...` (I fetched the live listing to confirm this layout). The published snapshot is rooted one level deeper at `.../Inbox/drafts/` and records `10.8 (isac)/10.8.1 (evaluations)/...` — 0 of its 321 files carry the `drafts/` prefix. File identity is "folder path + filename", so the same upload on both servers is never recognised as one file: it is stored twice and announced as new. That is the duplicate row and the "59 new file(s)" notice seen earlier.

## Steps

1. **Make the live crawl and the snapshot speak the same paths.**
   - Point the drafts probe at `.../RAN1/Inbox/drafts/` instead of `.../RAN1/Inbox/` (venue HTTPS, venue HTTP, and the sync mirror — direct and proxied). This also stops the probe picking up non-draft material sitting in the Inbox root (Tdoc lists, chair notes, loose `.zip` uploads).
   - Keep a safety net in the identity comparison: a leading `drafts/` segment is ignored, so a snapshot or a configured venue URL rooted either way still matches.
   - Result: one upload = one file, one unread mark, one event. No duplicate rows, no false "new file(s)" count.
2. **During the meeting week, the live tree is the truth.** When a live source answers, any snapshot file the live crawl did not list is marked as gone (`removedAt`, the field the UI already filters on), so archive leftovers such as 10.8.1 Round 1 disappear for everyone. Outside the meeting week nothing changes — the snapshot is still the only source, exactly as today.
3. **Never hide a file the crawl simply did not reach.** The crawler stops at a request cap (240 server-side, 1000 in the browser), so a missing file could mean "not on the server" or "folder never opened". A file is only marked gone when the live crawl actually opened its containing folder. The crawler gains a list of folders it really read; the merge consults it before hiding anything. If the containing folder was never read, the file stays visible.
4. **Unread counts follow.** Activity tallies skip files that are now marked gone, so a hidden file cannot keep a folder looking unread.
5. **Say what happened.** The Drafts source line gains a short note when files were hidden, e.g. "3 file(s) no longer on the meeting server are hidden" — so nobody wonders whether a document vanished. `How to Use` gets one line under "Good to know" saying that during the meeting week the list follows the live server, and that files the server no longer holds are hidden rather than deleted.
6. **Check it.**
   - New checks: the same file under either root stays one artifact with no new event; a snapshot file whose folder the live crawl opened disappears; a snapshot file whose folder was never opened stays; outside the meeting week nothing is hidden.
   - Live check in the preview on the RAN1#126bis Drafts page: no duplicate agenda rows, no `10.8.1 / Round 1` leftovers while the live mirror is being read, and the source line still names the server used.
   - `bunx tsgo --noEmit` and the normal build must stay clean.
7. **Publish** so ran1.app carries this together with the agenda changes already waiting.

## Technical details

- `src/services/draftLiveSource.ts`
  - `SYNC_DRAFTS_BASE`, `VENUE_DRAFTS_BASE`, `VENUE_DRAFTS_BASE_HTTPS`: append `drafts/`; a configured venue URL ending in `Inbox/` gets the same treatment (its `includes("/Meetings_3GPP_SYNC/RAN1/Inbox/")` guard still passes).
  - `identity()` / the merge key: normalise away a leading `drafts/` segment on both sides.
  - `mergeLive()`: after merging, mark unmatched snapshot artifacts and folders `removedAt` when their containing folder is in the crawl's read-folders set; report the count on the returned report.
- `src/lib/listingParser.ts`: `walkListing` returns the set of folder paths whose listing was actually fetched (`readFolders`), so the merge can tell "absent" from "not looked at".
- `src/lib/drafts.functions.ts` + `src/lib/syncCrawl.server.ts`: pass `readFolders` through the server proxy response alongside `folders` and `files`.
- `src/services/draftService.ts`: `buildActivity` skips events for artifacts marked gone; the drafts pages filter on `removedAt` already, so no page changes are needed beyond the new note.
- `src/types/drafts.ts`: `LiveDraftReport` gains `hiddenCount` (or equivalent) for the note.
- The GitHub Action snapshot keeps crawling the meeting folder as the baseline — untouched.

## After this plan (one at a time, as agreed)

- **Branch drafts under followed sub-items**: files filed at 10.7 still need to show under a followed 10.7.1, and the reason the earlier check showed nothing needs confirming.
- **Your side**: add the two GitHub secrets for the remote meeting FTP, then confirm a real summon alert reaches both devices.
