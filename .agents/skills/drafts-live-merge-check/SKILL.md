---
name: drafts-live-merge-check
description: Verify the RAN1 Live! drafts list is a clean merge of the meeting server and the committed snapshot — no duplicate documents, hidden files explained, every folder actually opened. Use when drafts look duplicated, missing, stale, or "old files are showing".
---

# Drafts live-merge check

Three trees can feed the drafts list: the venue server (`https://10.10.10.10`),
the 3GPP sync mirror, and the per-meeting archive. Duplicates and leftovers come
from the merge, so test the merge rather than staring at the page.

## Steps

1. Offline checks against fixtures (fast, no network):

   ```
   bun run check:draft-merge
   ```

2. Real-data checks against the live meeting server:

   ```
   bun run check:draft-merge-live
   ```

   Read the summary it prints: folders opened, files found, and duplicate
   identities — **duplicates must be zero**. A hidden count is fine as long as
   each hidden file is one the live server really dropped.

3. See what the site will show:

   ```
   python3 -c "import json;d=json.load(open('public/data/meetings/<slug>/drafts.json'));print(d['scanState'],d['lastSuccessfulScanAt'],len(d['folders']),len(d['artifacts']))"
   ```

4. Then open `/drafts` at a phone viewport. The note about hidden files must
   account for anything the meeting server dropped, and no folder heading may
   list the same document twice.

## Rules the merge must keep

- A leading `drafts/` in a path means the same place in both roots: normalise it,
  never treat it as a second folder — that is how one document becomes two rows.
- A file the live server no longer holds is **hidden, never deleted**, and only
  when the crawl actually opened its containing folder.
- Anything in a folder the crawl never reached stays visible: absence from a
  listing you never read is not evidence.
- Live sources are read only during the meeting week. Before it, the archive is
  the only source, because the mirror still holds the previous meeting's files.
- Refresh jobs share one commit queue (`data-refresh`) and rebase-retry — two
  jobs pushing the same branch is normal, not a failure.

Related: `meeting-week-refresh` for the timetable, `new-meeting-setup` before the
week, `publish-and-verify` when the site itself changed.
