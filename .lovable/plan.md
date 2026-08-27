# Make venue mode automatic and fix the URI-too-long hop

## What you just hit

The hop URL you saw (`3gpplive.net/?ran1import=...`) is so long that GitHub Pages returns **Error: URI Too Long**. The blob currently carries your entire cached meetings index (`ran1live.meetings.v1`), which is tens of kilobytes when base64-encoded. Browsers and servers commonly reject URLs above ~8 KB.

## Why the URL exists at all

`ran1.app` (HTTPS) and `3gpplive.net` (HTTP) are different origins, so the app cannot use `localStorage`, `postMessage`, or cookies to move your preferences across. The only portable way to pass state without a server is the URL. It is cleaned from the address bar the instant the twin loads, but it has to be small enough to travel.

## What will change

1. **Transfer only preferences, not cached data.** The blob will carry only:
   - company name / group / userId
   - bookmarks and followed drafts
   - the "always switch" preference
   - current meeting/room selection
   It will **not** carry the full meetings list, draft index, or any other cache that the twin can re-fetch on its own.
2. **Auto-hop without a probe.** The mixed-content fetch probe to `http://3gpplive.net` always fails from an HTTPS page, so auto-hop never worked. When the toggle is on and a meeting is active, `ran1.app` will redirect immediately with `window.location.replace`.
3. **Visible "Always open venue mode" checkbox on the offer banner.** Right now the banner has two buttons and no state indicator. The checkbox will show whether auto-hop is enabled and let you turn it off from either side.
4. **HTTPS-on-twin warning.** If someone lands on `https://3gpplive.net` directly, the twin will show a warning reminding them to use `ran1.app` instead. With GitHub Pages "Enforce HTTPS" unchecked this should not pin HSTS, but the warning makes the mistake obvious.
5. **Recover-from-dead-twin button.** Once on the HTTP twin, if the meeting-room server at `10.10.10.10` is not reachable, the banner will offer **Back to ran1.app** and clear the auto-hop toggle so you are not stuck on the twin.

## Files to touch

- `src/lib/venueMode.ts` — shrink `collectLocalState()` to a fixed allow-list of preference keys; remove the probe from `autoHopToVenue()`; add HTTPS-twin detection.
- `src/components/VenueModeBanner.tsx` — instant auto-hop in effect; checkbox in offer state; dead-twin return action.
- `docs/HOW-TO-USE.md` — update the venue-mode section.

## About `ran1.net`

A separate alias domain would still need to be a plain-HTTP-capable domain of its own (not a subdomain of `ran1.app`, because `ran1.app` sends HSTS with `includeSubDomains`). It would not remove the need for the import blob, but the blob will be small after this fix. Keeping `3gpplive.net` and making the hop silent is the simplest path; users never need to type or bookmark the twin address.
