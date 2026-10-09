# Make notification setup obvious on phones

## Problem
On the user's phone nothing asked them to install the app or enable notifications. Two root causes:
1. The new version was never published — the phone still runs the old app with no Notifications card.
2. Browsers never auto-prompt for home-screen install or notifications; the user must act, and the app currently gives no guidance. On iPhone, push only works from the installed home-screen app, and a previously-installed-then-deleted app does not change that.

## Changes

1. **Smarter Notifications card on the Company page** (`src/routes/company.tsx` + `src/hooks/usePushNotifications.ts`):
   - Detect iOS (`navigator.userAgent` / `navigator.standalone`) and whether the app runs installed (standalone display-mode).
   - iPhone in Safari (not installed): card shows "To get notifications: tap Share → Add to Home Screen, then open RAN1 Live from your home screen and come back here." No Enable button (it would fail silently on iOS Safari).
   - iPhone installed app / Android / desktop: show the Enable button as now.
   - Android Chrome no longer shows an automatic install prompt either; the card and help page give the manual steps: ⋮ menu → "Add to Home screen" / "Install app". (Installing is optional on Android — push works in plain Chrome too.)
   - After enabling, confirm with a short "You're all set" state.

2. **Help page** (`src/routes/help.tsx`): expand the notifications bullet with the exact per-device steps — iPhone: Share → Add to Home Screen → open the installed app → Company → Enable (a previously deleted install doesn't matter, just add it again); Android: optionally install via ⋮ → "Add to Home screen" / "Install app", then Company → Enable (works in plain Chrome too).

3. **Rename the app to "RAN1 Live!"** everywhere it is user-visible:
   - `public/manifest.webmanifest` (`name`, `short_name`) — this is the home-screen icon label.
   - Page titles and meta (route `head()` titles, e.g. "How to use RAN1 Live!"), the app header/logo text, and help-page copy.
   - Note: users who already installed the app keep the old icon label until they re-add it (phones cache the name at install time).

4. **Publish** so the phone actually receives the new version (frontend changes only go live on publish).

## Notes
- No auto-prompt is possible: iOS requires the user to add the app manually, and notification permission can only be requested from a user tap — hence the guided card.
- Android/desktop are unaffected: Enable works directly in the browser.
