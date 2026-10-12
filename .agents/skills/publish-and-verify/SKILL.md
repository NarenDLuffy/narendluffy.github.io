---
name: publish-and-verify
description: Publish RAN1 Live! and prove the change really reached the live site at ran1.app. Use when the user asks to publish, deploy, ship or go live, and before ever claiming a fix is "live".
---

# Publish and verify

Frontend changes reach the live site only through a publish; backend and data
changes do not. So "the code is fixed" is not "the site is fixed" until this has
been run.

1. Read the security scan first (`security--get_scan_results`). If it is missing,
   stale or still running, run `security--run_security_scan` and wait. Surface
   anything critical to the user before publishing.
2. Publish with `preview_ui--publish`. Its success only proves the publish was
   *requested* — deployment takes about a minute, a few more for custom domains.
   Never report "live" from that call alone.
3. Verify the way a delegate sees it, not the way a build log does:
   - `curl -s -o /dev/null -w '%{http_code}' https://ran1.app/<route>` → 200.
   - Playwright at a phone viewport (390×844) on the route that changed:
     screenshot it, read the console, and confirm the actual change is visible.
4. Data-only change? Then no publish is needed — the app reads the repo copy
   live. Prove it with the timestamp inside the data file instead.
5. Tell the user what they will now see, in their words.

## Standing limits

- The site reads generated data from the repo copy first, bundled copy as
  fallback, so a stale-looking page is usually a cached tab: reload before
  chasing the code.
- Server functions are versioned with the build: a tab opened before a publish
  can call an old function id and get a 500. That is a stale tab, not a bug.
- Publishing never changes visibility and cannot unpublish; unpublish is a
  button in Project settings.

Related: `meeting-week-refresh` and `drafts-live-merge-check` cover the data
paths that need no publish; `new-meeting-setup` ends with this one.
