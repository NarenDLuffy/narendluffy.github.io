# Drafts: add HTTPS venue server, keep the all-sources probe

## Scope (per your correction)

The probe logic stays: it looks at all three sources — venue server
(`10.10.10.10`), Meetings Sync mirror, and the per-meeting archive folder —
and the freshest upload wins, with `mergeLive` deduping by agenda path +
filename so one upload stays ONE artifact. The only functional change is that
the venue server is also tried over **HTTPS**.

## Current state (verified in code)

- `VENUE_DRAFTS_BASE` is hardcoded to `http://10.10.10.10/...` and the venue
  candidate is skipped on every `https://` page (`venueBlockedByScheme()`) —
  an HTTPS venue server would never be tried.
- The probe stops at the first candidate that returns files. To honour "use
  whichever is latest", every reachable candidate's crawl is merged instead of
  stopping early — `mergeLive` already handles the dedup, so this is a small
  loop change.
- The meeting archive folder is not a live candidate in the app today; the
  server proxy is locked to the SYNC prefix. It is added as the third source
  via the proxy (allowlist widened to any URL under `https://www.3gpp.org/ftp/`).
- The backend can never reach `10.10.10.10` itself (private LAN address);
  venue access is always browser-side.

## Changes

### 1. HTTPS venue candidate (`src/services/draftLiveSource.ts`)

- Venue candidates become `https://10.10.10.10/...` and
  `http://10.10.10.10/...`, https tried first.
- Gating: only skip an `http://` venue candidate on an `https://` page (mixed
  content). An `https://` venue candidate is attempted from `https://ran1.app`
  too, so an HTTPS venue server works directly — no twin, no banner.
- A user-configured local-source URL keeps working as today.

### 2. Merge all reachable sources instead of stopping at the first

- `probeLiveDrafts` crawls every candidate that can answer and merges each
  result over the published index; the freshest file from any source shows up.
- `origin`/`baseUrl` in the report reflect the source that contributed the
  newest content; status text stays honest about which sources answered.

### 3. Meeting archive folder as the third source

- Widen the proxy allowlist (`src/lib/drafts.functions.ts` +
  `syncCrawl.server.ts`) to any URL under `https://www.3gpp.org/ftp/`.
- Add a `meeting-archive` proxy candidate using the meeting's own
  `sources.meetingFolder` URL.

### 4. Status text

- `blocked-mixed-content` only for the http attempt from an https page.
- Failed https venue attempt reports `unavailable` (not on the network, cert
  not trusted, or no CORS headers — all look the same to the browser).

### 5. Venue twin plumbing untouched

`venueMode.ts` and the HTTP twin stay as they are (`VENUE_MODE_ENABLED` false).

## External requirements (not code)

- Venue HTTPS needs a certificate valid for the IP `10.10.10.10` — self-signed
  fails silently in `fetch`.
- The venue server must send `Access-Control-Allow-Origin` on listings (the
  fetch is cross-origin whatever the scheme — same requirement as the HTTP
  twin today).

## Expected result

- If the venue server is reachable over HTTPS, `https://ran1.app` reads drafts
  from it directly, on meeting Wi-Fi, with no switching.
- All three sources are checked every refresh; whichever has the newest upload
  is what you see, with no duplicates.
