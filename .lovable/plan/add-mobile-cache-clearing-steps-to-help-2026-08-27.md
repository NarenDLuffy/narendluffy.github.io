# Add mobile cache-clearing steps to Help

## Problem
When a browser pins `3gpplive.net` to HTTPS (HSTS), the venue twin loads as HTTPS and shows the "Venue mode opened over HTTPS" warning. Users need step-by-step instructions to clear stored site data on iOS Safari and Android Chrome so the next hop from `https://ran1.app` stays plain HTTP.

## What to build
Add a short, mobile-focused troubleshooting guide in two places:

1. **In-app Help page** (`src/routes/help.tsx`)
   - Add a new "Venue mode" section near the bottom that explains:
     - Why the twin must use HTTP (browser mixed-content block).
     - That the warning means the browser cached HTTPS for `3gpplive.net`.
     - iOS Safari steps: Settings → Safari → Clear History and Website Data, or Advanced → Website Data → delete `3gpplive`.
     - Android Chrome steps: Chrome → History → Clear browsing data → Advanced → Cookies and site data + Cached images and files.
     - Reminder to always enter via `https://ran1.app`, never `https://3gpplive.net`.

2. **Usage guide** (`docs/HOW-TO-USE.md`)
   - Extend the existing "Venue mode" section with the same cache-clearing steps.
   - Keep the existing verified URL table.

## Out of scope
- No code changes to venue-mode logic or components.
- No new routes or navigation changes.

## Verification
- Build the app and open `/help`.
- Confirm the new section renders correctly on mobile viewport.
- Confirm `docs/HOW-TO-USE.md` still renders correctly in the repo preview.