# Drafts source priority: venue (HTTPS-capable) → sync mirror → meeting archive (pre-meeting)

## Confirmed understanding

- **During the meeting week:** uploads appear first on the venue server
  (`10.10.10.10`), then replicate to the public Meetings Sync mirror roughly
  every 15 minutes. The per-meeting archive folder does not matter then.
- **Before the meeting week (like right now):** everything is uploaded to the
  per-meeting folder (`/ftp/tsg_ran/WG1_RL1/TSGR1_126b/`), so that is the live
  source until the week starts.

So the live probe order is:

- Meeting active: **venue → sync mirror → published snapshot**
- Meeting upcoming: **meeting archive folder → published snapshot**

One upload stays ONE artifact across all sources: `mergeLive` dedups by agenda
path + filename, so the same file seen on two servers never duplicates or
re-notifies. This mirrors the GitHub Action, which already uses the SYNC root
for active meetings and the archive folder otherwise.

## Current state (verified in code)

- The venue base is hardcoded to `http://10.10.10.10/...` and the venue
  candidate is skipped on every `https://` page — an HTTPS venue server would
  never be tried.
- The probe order is venue → sync proxy → direct sync; the meeting archive
  folder is NOT a live candidate in the app today (only GitHub Actions uses
  it), so pre-meeting uploads only appear after the Action commits.
- The server proxy is locked to the SYNC prefix, so it cannot yet crawl the
  archive folder either.
- The backend can never reach `10.10.10.10` itself (private LAN address);
  venue access is always browser-side.

## Changes

### 1. HTTPS-capable venue candidate (`src/services/draftLiveSource.ts`)

- Venue candidates become `https://10.10.10.10/...` and
  `http://10.10.10.10/...`, https tried first.
- Gating: only skip an `http://` venue candidate on an `https://` page (mixed
  content). An `https://` venue candidate is attempted from `https://ran1.app`
  too, so if the venue server goes HTTPS it becomes the primary source with no
  twin and no banner.
- A user-configured local-source URL keeps working as today.

### 2. Meeting archive as the pre-meeting live source

- Widen the proxy allowlist (`src/lib/drafts.functions.ts` +
  `syncCrawl.server.ts`) from the SYNC prefix to any URL under
  `https://www.3gpp.org/ftp/`, so a meeting's `sources.meetingFolder` can be
  crawled server-side.
- Add a `meeting-archive` proxy candidate, used only when the meeting is not
  active (upcoming/just before the week), using the meeting's own folder URL
  from its data. During the week it is skipped, per the confirmed timing.

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

- Right now (pre-meeting): the Drafts page shows uploads from the meeting
  folder live, without waiting for the GitHub Action.
- During the week on meeting Wi-Fi with an HTTPS venue server: `https://ran1.app`
  reads drafts directly from `10.10.10.10` — primary source, no switching.
- During the week off-site: sync mirror (live, ~15 min behind venue), then the
  published snapshot.
