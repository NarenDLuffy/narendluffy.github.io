# Fix Draft updates from public sync and venue Wi-Fi

## Confirmed diagnosis

- The published RAN1#126 draft index was last scanned on **25 Aug at 15:52 UTC** and contains **1,778 files**.
- Running the existing scanner now against the public Meetings Sync tree finds **1,933 files and 167 new events**, so the ingestion/parser works and the checked-in snapshot is stale.
- The public Sync URL is reachable, but browsers reject JavaScript access because the 3GPP server does not provide a CORS permission header. The app currently tries to fetch that URL directly from the browser, so its advertised live fallback cannot work.
- The venue source is `http://10.10.10.10/...`, while ran1.app is HTTPS. Safari blocks that request as insecure mixed content before local-network permission is considered. A toggle cannot override this browser security rule.
- Why the scheduled GitHub workflow has not committed the latest snapshot is not visible from the repository files; its execution history must be checked in GitHub Actions.

## Implementation

1. **Make Public Sync reliable on ran1.app**
   - Add a thin server function that fetches only allow-listed 3GPP Sync directory URLs.
   - Keep the existing recursive tree parser and merge/deduplication logic, but route Sync listing requests through this same-origin server function instead of fetching 3GPP directly from the browser.
   - Validate every requested URL so the function cannot become an open proxy.

2. **Keep GitHub Pages supported**
   - Static GitHub Pages has no server function, so it will use the regularly generated `drafts.json` snapshot.
   - Update the Drafts status text to distinguish “live sync” on ran1.app from “published snapshot” on GitHub Pages rather than implying a live browser fallback that cannot work.

3. **Repair and monitor snapshot automation**
   - Keep the current 10-minute meeting-week scan.
   - Add a workflow summary showing source URL, artifact count, new events, and scan timestamp.
   - Ensure a changed draft snapshot triggers the normal deployment workflow after the bot commit.
   - Document the one-time GitHub check if scheduled workflows are disabled or lack write permission.

4. **Handle the venue server honestly**
   - Do not add a misleading toggle: it cannot bypass HTTPS mixed-content or CORS restrictions.
   - Continue a short direct venue probe only where the browser permits it, and report the precise state: connected, browser-blocked, or unreachable.
   - Use live Public Sync automatically when venue access is blocked.

5. **Optional true venue bridge**
   - Add a small local uploader that one attendee runs on a laptop connected to meeting Wi-Fi. It reads `10.10.10.10`, sends only the normalized public draft index to an authenticated app endpoint, and makes the latest venue state available to every phone.
   - This is the only reliable way for an HTTPS website to consume a plain-HTTP, non-CORS LAN server without changes to that server.

## Verification

- Confirm ran1.app’s Refresh now returns the current Sync count instead of the stale 1,778-file snapshot.
- Confirm new and replicated files remain deduplicated.
- Confirm venue failure falls back to Sync with an accurate source/status message.
- Confirm GitHub Pages still loads the latest generated snapshot without server functions.