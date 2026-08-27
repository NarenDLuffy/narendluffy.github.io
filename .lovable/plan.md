# Drafts: venue server first, 3GPP sync second

## Answer to the proxy idea

A backend proxy is exactly right for the **sync mirror**, and I'll build it. But
it cannot work for **10.10.10.10**.

`10.10.10.10` is a private address that only exists inside the meeting-room
network. A Lovable server function runs in a datacenter, not on the venue Wi-Fi,
so when it tries `http://10.10.10.10/...` there is simply no such machine — it
times out. The blocker for the venue is not encryption, it's reachability: only
a device physically on that Wi-Fi can read it, i.e. the phone/laptop itself.

And a browser on that Wi-Fi will only be allowed to read `http://10.10.10.10`
if the page it is running is also plain `http://`. That is the one hard rule.

```text
venue server 10.10.10.10   reachable ONLY from a device on venue Wi-Fi
                           -> must be fetched by the browser, not the server
                           -> browser allows it only from an http:// page

3GPP sync mirror           public internet, blocked in-browser by CORS
                           -> perfect job for a backend proxy
```

## What I'll build

### 1. Sync mirror via a server function (works everywhere, today)

New server function on the Lovable app fetches and returns the
`/ftp/Meetings_3GPP_SYNC/RAN1/Inbox/` listings server-side, bypassing CORS. The
existing parser and `mergeLive` dedup logic stay unchanged, so a file that later
also appears on another server remains one artifact with one unread mark.
Result: https://ran1.app finally updates live from sync every refresh cycle,
instead of showing a stale committed snapshot.

### 2. Fresher committed snapshots

Audit and tighten the drafts GitHub Action so the stored index does not fall
behind (a manual scan found ~1,933 files versus ~1,778 in the published index).
This is what cold loads and any static copy read.

### 3. Venue mode — an HTTP twin of the same app

The main app stays on Lovable at https://ran1.app. In addition, the same build
is deployed as a static copy to GitHub Pages under a hostname where HTTPS is not
forced, e.g. `http://venue.ran1.app`. Same code, same UI, one extra deploy
target in the existing Pages workflow — no scripts, no laptop, nothing for
colleagues to install.

Because that page is plain HTTP, the browser permits it to crawl
`http://10.10.10.10/...` directly, which is the only path that works in the room.

Switching is handled for the user:

- On https://ran1.app the Drafts page runs a fast, silent probe for the venue
  server. If it looks like venue Wi-Fi, a banner appears: "You're at the venue —
  open venue mode", one tap, same route, follows/bookmarks carried across.
- A "remember this" option makes future venue detections switch automatically.
- On the HTTP twin, venue crawling is on by default; if the venue server drops
  away it falls back to the snapshot and tells you so.
- Check-ins and anything account-backed stay on the HTTPS site; the twin links
  back rather than sending anything sensitive over HTTP.

### 4. Honest status text in Drafts

Replaces today's vague "unavailable":

- `Venue server — live (N files, checked 12s ago)`
- `Venue server blocked — this page is HTTPS. Open venue mode` + button
- `Not on the meeting network — using 3GPP sync (live)`
- `3GPP sync unavailable — snapshot from <time>`

## Technical details

- `src/lib/drafts.functions.ts` (new): `fetchSyncListing({ url })` server fn.
  Validates the URL is under `https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN1/`,
  fetches, returns raw HTML for the existing `parseListing`. Bounded
  request count and depth, short server-side cache.
- `src/services/draftLiveSource.ts`: add a `sync-proxy` candidate that calls the
  server fn; when `location.protocol === 'https:'` mark venue as
  `blocked-mixed-content` instead of attempting and reporting "unavailable".
- `src/lib/venueMode.ts` (new): venue detection beacon, HTTP-twin URL builder,
  transfer of follows/bookmarks, and the "always switch" preference.
- `src/routes/drafts.index.tsx`: venue banner and the precise status strings.
- `.github/workflows/deploy-pages.yml`: publish the venue host (CNAME for
  `venue.ran1.app`, HTTPS enforcement left off for that hostname only).
- `.github/workflows/update-drafts.yml`: confirm the schedule runs and commits;
  shorter interval during meeting weeks.

## What's needed from you

Only for step 3: point `venue.ran1.app` at GitHub Pages and leave "Enforce
HTTPS" unchecked for it. I'll prepare the workflow and give you the exact DNS
records. Steps 1, 2 and 4 need nothing from you and improve ran1.app as it is
hosted today.
