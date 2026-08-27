# Keep the current GitHub Pages venue setup

## Goal
Keep `3gpplive.net` on GitHub Pages and make the app accurately handle phones where Chrome upgrades venue mode to HTTPS.

## Changes
1. Keep the existing GitHub Pages deployment, domain, and `http://3gpplive.net` link unchanged.
2. Replace the misleading cache-clearing/retry guidance shown on the HTTPS twin. The live checks confirm GitHub Pages serves a valid HTTPS version, so Chrome can upgrade successfully even after cache clearing.
3. Show a concise HTTPS venue warning that:
   - explains that direct access to `10.10.10.10` is unavailable in this browser session;
   - confirms that schedule and drafts will continue through the public meeting-sync source;
   - provides a clear return action to `ran1.app`;
   - allows automatic venue opening to be disabled.
4. Update the Help documentation to describe the limitation and remove instructions that imply clearing cache guarantees HTTP access.
5. Verify both states in the browser: normal `ran1.app` operation and the HTTPS venue-twin fallback.

## Technical notes
- No backend, DNS, hosting, or schedule-ingestion changes.
- Direct venue access will still work on browsers/devices that actually permit the HTTP URL.
- On Chrome configurations that upgrade HTTP to the valid GitHub Pages HTTPS endpoint, the public sync fallback is the supported behavior.
