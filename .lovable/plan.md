# Venue server (10.10.10.10) access

## The real blocker

The app is served over HTTPS (ran1.app / github.io). The venue server is plain HTTP at
`http://10.10.10.10/...`. Browsers block HTTPS pages from loading HTTP resources
(mixed content) — Safari/iOS blocks it silently, which is why no local-network
prompt ever appears on iPhone.

So a toggle alone cannot make it work: the browser refuses the request regardless
of app settings. A toggle is still useful, but it needs an escape hatch alongside it.

## What to build

1. **Venue mode toggle** (Drafts page + Settings area)
   - "Try venue server (10.10.10.10)" on/off, stored locally, default on.
   - When off, the app never attempts the local request (no permission prompt,
     no console noise) and goes straight to the public sync mirror.
   - Editable venue base URL for meetings where the address differs.

2. **Honest status line with a working path forward**
   - After a probe, show one of: Connected to venue server / Blocked by browser
     (HTTPS to HTTP) / Not reachable on this network / Disabled.
   - When "Blocked", offer the escape hatch below instead of a dead end.

3. **HTTP mirror of the app for venue use** (the actual fix)
   - Publish the same static build to an HTTP-reachable URL and link to it from
     the blocked state as "Open venue edition".
   - From an HTTP page, requests to `http://10.10.10.10` are same-scheme, iOS
     shows the local-network prompt, and Drafts sync properly.
   - If no HTTP host is available, fall back to option 4.

4. **Manual venue import fallback**
   - A "Paste venue listing" box: the user opens `http://10.10.10.10/ftp/.../Inbox/`
     in a browser tab, copies the page, pastes it in, and the existing HTML
     directory-listing parser ingests it into the same dedup/index pipeline.
   - Also accept a dropped `.zip`/file list. No new backend needed.

## Technical notes

- `src/services/draftLiveSource.ts`: add `venueEnabled` + `venueBaseOverride`
  settings, classify failures as `blocked` (mixed content / TypeError before any
  network) vs `unreachable` (timeout), reuse the existing listing parser for
  pasted HTML.
- `src/services/draftService.ts` / `src/hooks/useDrafts.ts`: pass the new
  status and settings through; `refreshNow` respects the toggle.
- `src/routes/drafts.index.tsx`: toggle UI, status chip, paste-import dialog.
- Help page: short "At the venue" section explaining HTTP vs HTTPS.

## Decision needed

Do you have (or want) an HTTP-served copy of the app for venue use? If not, I
build items 1, 2 and 4 only, and the paste-import becomes the venue path on iPhone.
