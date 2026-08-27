# Fix: http://venue.ran1.app is force-upgraded to HTTPS

## What I verified just now

Two live checks against the real hosts:

- `http://venue.ran1.app/` returns **HTTP/1.1 200 OK** from GitHub with **no redirect**. GitHub Pages is configured correctly and "Enforce HTTPS" is genuinely off.
- `https://ran1.app/` returns the header `strict-origin-when-cross-origin` plus:
  `strict-transport-security: max-age=31536000; includeSubDomains`
- `https://venue.ran1.app/` also returns `strict-transport-security: max-age=31556952` from GitHub.

## Diagnosis

The problem is not GitHub and not DNS. It is HSTS in the browser.

`ran1.app` sends HSTS with **includeSubDomains** and a one-year lifetime. Once any browser has loaded `https://ran1.app` even once, that browser records a rule: "never use plain HTTP for ran1.app **or any subdomain of it**, for the next year." `venue.ran1.app` is a subdomain, so the browser rewrites `http://venue.ran1.app` to `https://` internally, before any request leaves the device. GitHub never sees the HTTP request — which is why GitHub still shows the site as HTTP while your browser shows HTTPS.

Consequence: **the venue twin can never be a subdomain of ran1.app.** No GitHub setting can fix this, because the HTTPS upgrade happens inside the browser.

A second, smaller problem: GitHub Pages sends its own HSTS header on the HTTPS version of any custom domain. So even on a fresh domain, if a user ever lands on the HTTPS version once, that host gets pinned to HTTPS for that browser too.

```text
browser types http://venue.ran1.app
        |
        v
  HSTS rule from ran1.app (includeSubDomains)  -->  rewrite to https://
        |
        v
  request leaves as HTTPS  -->  GitHub serves it, mixed content still blocked
```

## Options

### Option A — Move the venue twin to a separate domain (recommended)

Use a hostname that is not under `ran1.app`, for example `ran1venue.net` or any cheap second domain you own.

1. Register a second domain (any registrar, roughly 10 EUR/year).
2. Point its apex (or a subdomain like `venue.<newdomain>`) at GitHub Pages with a CNAME to `narendluffy.github.io`.
3. In the repo: Settings -> Pages -> Custom domain -> the new hostname, and leave "Enforce HTTPS" unchecked.
4. Update the `VENUE_HOST` repository variable to the new hostname and re-run the deploy workflow.
5. Remove `venue.ran1.app` as the Pages custom domain so it stops being confusing.

Important: always link to the twin as an explicit `http://` URL, and never open its HTTPS version, or GitHub's own HSTS header will pin that host too.

### Option B — Ask Lovable support to drop includeSubDomains on ran1.app

If the HSTS header on `ran1.app` could be changed to omit `includeSubDomains`, `venue.ran1.app` would work. This is a platform-level header on Lovable's edge, so it is not something we can change from the codebase, and it weakens security for the main site. Only worth pursuing if Option A is unacceptable.

### Option C — Drop the HTTP twin, use a manual venue import

Instead of the twin, add an in-app "Import venue listing" flow: the user opens `http://10.10.10.10/` directly in a browser tab (which always works), copies the directory listing or saves the page, and pastes/drops it into the Drafts page. The app parses it with the existing listing parser and merges it into the draft index. Slower and manual, but it needs no second domain and no HSTS gymnastics.

## Code changes needed regardless of the option chosen

1. **Honest venue-mode detection.** `src/components/VenueModeBanner.tsx` currently assumes that if the page protocol is `http:` it is in venue mode. Add the inverse case: if the user arrived with the `ran1import` transfer parameter but the page is on `https:`, the hop was silently upgraded. Show a clear explanation ("your browser forced HTTPS; venue mode is unavailable on this device") instead of silently falling back.
2. **Stop the redirect loop risk.** In `src/lib/venueMode.ts`, do not auto-switch (`alwaysSwitch`) when the previous hop already failed; record the failure so the app does not bounce the user between hosts.
3. **Update `VENUE_HOST`.** It is read from `VITE_VENUE_HOST` at build time with a `venue.ran1.app` fallback in `src/lib/venueMode.ts`. Change the fallback to whatever host we settle on.
4. **Update docs.** `docs/HOW-TO-USE.md` and `README.md` both name `venue.ran1.app`; correct them and add a short note that the twin must live on a separate domain because of HSTS.

## Decision needed

Which option do you want? Option A is the only one that makes venue mode actually work as designed, but it requires a second domain.
