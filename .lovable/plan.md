# Drafts source priority: venue (HTTPS-capable) → sync mirror → meeting archive

## Confirmed understanding

Yes, correctly understood. During the meeting week, uploads appear first on the
venue server (`10.10.10.10`), replicate to the public Meetings Sync mirror
roughly every 15 minutes, and only much later land in the per-meeting archive
folder (e.g. `/ftp/tsg_ran/WG1_RL1/TSGR1_126b/Inbox/`). So the live probe
should try, in order:

1. **Venue server** — fastest, only reachable on the meeting Wi-Fi.
2. **Meetings Sync mirror** — works everywhere via the server proxy.
3. **Meeting archive folder** — slowest, but sometimes has files sync missed.
4. Published snapshot — what cold loads already show.

One upload stays ONE artifact across all of these: `mergeLive` dedups by agenda
path + filename, so the same file seen on two servers never duplicates or
re-notifies.

## Current state (verified in code)

- The venue base is hardcoded to `http://10.10.10.10/...` and the venue
  candidate is skipped on every `https://` page — an HTTPS venue server would
  never be tried.
- The probe order is already venue → sync proxy → direct sync; the meeting
  archive folder is NOT a live candidate today (only GitHub Actions uses it).
- The server proxy is locked to the SYNC prefix, so it cannot yet crawl the
  archive folder either.
- The backend can never reach `10.10.10.10` itself (private LAN address);
  venue access is always browser-side. That is fine — it is candidate #1
  precisely because only on-site devices can see it.

## Changes

### 1. HTTPS-capable venue candidate (`src/services/draftLiveSource.ts`)

- Venue candidates become `https://10.10.10.10/...` and
  `http://10.10.10.10/...`, https tried first.
- Gating: only skip an `http://` venue candidate on an `https://` page (mixed
  content). An `https://` venue candidate is attempted from `https://ran1.app`
  too, so if the venue server goes HTTPS it becomes the primary source with no
  twin and no banner.
- A user-configured local-source URL keeps working as today.

### 2. Meeting archive as third candidate

- Widen the proxy allowlist (`src/lib/drafts.functions.ts` +
  `syncCrawl.server.ts`) from the SYNC prefix to any URL under
  `https://www.3gpp.org/ftp/`, so the active meeting's `sources.meetingFolder`
  can be crawled server-side.
- Add a `meeting-archive` proxy candidate after sync-proxy, using the meeting's
  own folder URL from its data.

### 3. Honest status text

- `blocked-mixed-content` only for the http attempt from an https page.
- Failed https venue attempt reports `unavailable` (not on the network, cert
  not trusted, or no CORS headers — all look the same to the browser).

### 4. Venue twin plumbing untouched

`venueMode.ts` and the HTTP twin stay as they are (`VENUE_MODE_ENABLED` false);
with an HTTPS venue server the twin simply becomes unnecessary.

## External requirements (not code)

- Venue HTTPS needs a certificate valid for the IP `10.10.10.10` — self-signed
  fails silently in `fetch`.
- The venue server must send `Access-Control-Allow-Origin` on listings (the
  fetch is cross-origin whatever the scheme — same requirement as the HTTP
  twin today).

## Expected result

- On meeting Wi-Fi with an HTTPS venue server: `https://ran1.app` reads live
  drafts directly from `10.10.10.10` — primary source, no switching.
- Off-site or venue down: sync mirror (live, ~15 min behind venue), then the
  meeting archive folder, then the published snapshot.
