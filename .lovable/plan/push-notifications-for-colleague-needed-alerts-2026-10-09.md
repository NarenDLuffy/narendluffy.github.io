# Push notifications for "colleague needed" alerts

## Goal
When someone taps a colleague to summon them, every company member gets a real system notification on their phone/laptop — even if the app is closed — not just the in-app banner.

## How it works
- Standard Web Push (VAPID): works on Android Chrome and desktop browsers directly; on iPhone it requires the app to be added to the home screen first (Apple's rule for web push).
- The app already has a manifest and icons; we add `display: "standalone"` so it can be installed to the home screen (required for iOS push).

## Changes

1. **Push service worker** (`public/push-sw.js`, messaging-only — no offline caching):
   - Receives push events, shows a notification: "Alice is needed in Room 1 (Main)" with the time.
   - Tapping the notification opens the app on that room's page.

2. **Subscription storage** — new `push_subscriptions` table:
   - group_key (hashed company code), user_id, endpoint, keys, created_at.
   - RLS on, no direct client access; service-role grant (same pattern as company_alerts).

3. **Server functions** (`src/lib/push.functions.ts`):
   - `subscribePush` / `unsubscribePush` — save/remove the device's subscription, scoped to the company code.
   - `sendCompanyAlert` (existing) extended: after inserting the alert, look up all subscriptions for that group and send a web-push message to each; expired/dead endpoints are cleaned up.
   - VAPID keys: generate a keypair; public key as a `VITE_` env var, private key as a backend secret. Signing uses Web Crypto (worker-safe, no Node-only libraries).

4. **Client wiring** (`src/hooks/usePushNotifications.ts` + Company page):
   - "Enable notifications" button on the Company page: requests permission, registers the push service worker, subscribes, and stores the subscription under the company code.
   - Shows current state (enabled / blocked / not supported) so it's clear on each device.
   - Registration is production-only — never in the Lovable preview — per platform rules.

5. **Keep the existing banner** as the in-app fallback; push is additive.

6. **Update the "How to Use" page** (`src/routes/help.tsx`):
   - New section for the colleague summon feature: tap a colleague's name to alert the company, banner shows for 10 minutes, anyone can close it for themselves, sender can withdraw.
   - New section for push notifications: how to enable them per device, and the iPhone requirement to add the app to the home screen first.

## Technical notes
- No Firebase; plain VAPID web push avoids extra accounts and works with the existing backend.
- Service worker is a dedicated messaging worker (allowed), not an app-shell cache, so no offline/PWA caching behavior changes.
- iOS caveat: each iPhone user must add the app to their home screen once, then enable notifications inside it. Android/desktop just need the one-time permission prompt.
- Testing push end-to-end requires the published app (HTTPS + production), so verification happens after publish on your devices.
