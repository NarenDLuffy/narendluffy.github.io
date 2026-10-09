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
   - After enabling, confirm with a short "You're all set" state.

2. **Help page** (`src/routes/help.tsx`): expand the notifications bullet with the exact iPhone steps (Share → Add to Home Screen → open the installed app → Company → Enable), noting that deleting a previous install doesn't matter — just add it again.

3. **Publish** so the phone actually receives the new version (frontend changes only go live on publish).

## Notes
- No auto-prompt is possible: iOS requires the user to add the app manually, and notification permission can only be requested from a user tap — hence the guided card.
- Android/desktop are unaffected: Enable works directly in the browser.
