# Support an HTTPS venue server at 10.10.10.10

## Answer to the question

- **Backend:** No, and it never can. `10.10.10.10` is a private address that only
  exists on the meeting Wi-Fi, so a datacenter server function has no route to
  it. The sync proxy stays locked to the public 3GPP tree by design.
- **Code:** Not as-is. Two hardcoded assumptions block an HTTPS venue server:
  1. `VENUE_DRAFTS_BASE` is hardcoded to `http://10.10.10.10/...`, and
  2. the venue candidate is skipped on every `https://` page
     (`venueBlockedByScheme()`), so an HTTPS page never even tries.
- **Everything else already works:** the crawler, parser, and `mergeLive`
  dedup are scheme-agnostic. If the venue server is reachable over HTTPS, the
  same code path merges its files over the published index with no change.

## What changes in code

### 1. Scheme-flexible venue base (`src/services/draftLiveSource.ts`)

- Replace the single hardcoded `VENUE_DRAFTS_BASE` with two candidates:
  `https://10.10.10.10/...` and `http://10.10.10.10/...`.
- Candidate gating: only skip an `http://` venue candidate on an `https://`
  page (mixed content). An `https://` venue candidate is always attempted,
  including from `https://ran1.app`.
- A configured local-source URL keeps working exactly as today (only accepted
  when it points at the SYNC drafts Inbox).

### 2. Honest status text

- `blocked-mixed-content` is reported only for the http attempt from an https
  page.
- When an https venue attempt fails, report `unavailable` (it means the server
  is not on this network, its certificate is not trusted, or it sends no CORS
  headers — the UI keeps saying the venue server is simply not reachable).

### 3. Venue twin plumbing untouched

- `src/lib/venueMode.ts` and the HTTP twin stay as they are. With an HTTPS
  venue server the twin becomes unnecessary, but nothing breaks while it is off
  (`VENUE_MODE_ENABLED` remains false).

## External requirements (not code)

- The venue server needs a TLS certificate valid for the IP `10.10.10.10`.
  Browsers reject self-signed certificates silently in `fetch`, so a
  self-signed setup will not work.
- The venue server must send `Access-Control-Allow-Origin` on its directory
  listings. The fetch is cross-origin no matter the scheme, so this requirement
  is identical to today's HTTP case.

## Expected result

- If the venue server moves to HTTPS with a valid cert and CORS headers,
  `https://ran1.app` reads live drafts from it directly — no banner, no host
  switch, no HTTP twin.
- If it stays HTTP, behaviour is exactly as today: venue read only from the
  plain-HTTP twin, otherwise the 3GPP sync proxy.
