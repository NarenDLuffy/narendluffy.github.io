# Venue-first drafts: automatic 10.10.10.10 access, sync as fallback

## The constraint (why it fails today)

A page loaded over **https://** can never read **http://10.10.10.10/...** — every
browser blocks it as mixed content before any permission prompt appears. This is
not a setting we can toggle in code, and no server-side proxy can help either:
10.10.10.10 only exists on the venue Wi-Fi, and our server is not on that Wi-Fi.

So there are exactly two ways the venue server can be read with **no extra
laptop, no script, no new app**: the page itself must be loaded over plain
**http://**, from a device already on the venue Wi-Fi.

## The approach: an automatic HTTP twin of the same site

Keep one codebase and one domain. Serve the same app on a plain-HTTP host used
only at meetings, and make the switch automatic so nobody has to know about it.

```text
off-venue      https://ran1.app        -> sync mirror via server proxy (fallback)
at the venue   http://venue.ran1.app   -> crawls 10.10.10.10 directly (primary)
                     ^ app auto-detects and offers/performs the hop
```

- The HTTP twin is a static export of the same build (the GitHub Pages
  deploy workflow already produces it), published on a host with HTTPS
  enforcement off for that name only. No second image to maintain: same
  commit, same UI, one extra deploy target in the existing workflow.
- On https://ran1.app the Drafts page silently probes for the venue server via
  an image/`fetch` beacon that fails fast. If the probe suggests venue Wi-Fi,
  the app shows a one-tap "You're at the venue — switch to venue mode" banner
  that jumps to the HTTP twin at the same route, carrying follows/bookmarks
  over in the URL so nothing is lost. Optional "always switch at venues"
  remembers the choice and hops automatically next time.
- On the HTTP twin, venue crawling is on by default and Drafts shows
  "Venue server — live" with the file count and last check time. If the venue
  server disappears (left the room), it degrades to the sync path automatically.

Security note: the HTTP twin is read-only public schedule/draft data. Presence
check-ins and anything backend-authenticated stay on the HTTPS site; the twin
links back to it for those actions rather than sending credentials over HTTP.

## Fallback path when 10.10.10.10 is unreachable

1. **Server-function proxy for the 3GPP sync mirror.** The browser cannot crawl
   `/ftp/Meetings_3GPP_SYNC/RAN1/Inbox/` directly (CORS). A server function on
   ran1.app fetches and parses the listing server-side and returns the entries,
   so the published app updates live, every 60s, with the same dedup/merge rules
   already in `mergeLive`.
2. **More frequent snapshots.** Audit and tighten the drafts GitHub Action so
   the committed `drafts.json` stays close to live (it is currently behind:
   a manual scan found ~1,933 files vs ~1,778 in the published index). This is
   what the static github.io export and cold loads read.

## Honest status in the UI

Drafts replaces the vague "unavailable" with the real reason:

- `Venue server — live (N files, updated 12s ago)`
- `Venue server blocked — this page is HTTPS. Switch to venue mode` (with button)
- `Venue server not reachable — not on the meeting network. Using 3GPP sync.`
- `3GPP sync — live via proxy` / `Snapshot from <time>` when the proxy fails.

## Technical details

- `src/services/draftLiveSource.ts`: add an origin-scheme check; when
  `location.protocol === 'https:'` mark venue as `blocked-mixed-content` instead
  of attempting and reporting "unavailable". Add a `sync-proxy` candidate that
  calls the new server function instead of fetching 3GPP directly.
- New `src/lib/drafts.functions.ts`: `fetchSyncListing({ url })` server fn —
  validates the URL is under `https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN1/`,
  fetches, returns raw HTML for the existing `parseListing` to handle. Bounded
  depth/requests server-side, cached ~30s.
- New `src/lib/venueMode.ts`: venue detection beacon, HTTP-twin URL builder,
  state transfer of follows/bookmarks, and the "always switch" preference.
- `src/routes/drafts.index.tsx`: venue banner + precise status strings.
- `.github/workflows/deploy-pages.yml`: add the venue host output (CNAME +
  HTTPS-enforcement off for that hostname).
- `.github/workflows/update-drafts.yml`: verify the schedule actually runs and
  commits; shorten the interval during meeting weeks.

## What is needed from you

The HTTP twin needs one hostname where HTTPS is not forced (e.g.
`venue.ran1.app` pointed at GitHub Pages with "Enforce HTTPS" unchecked). I set
up the workflow and DNS instructions; you flip that one checkbox once.
