# Fix "Not connected — Missing Supabase environment variables" on ran1.app

## What the message means
Nothing checks GitHub. On ran1.app, when you check in, the live site's server tries to reach the shared check-in list and finds its backend connection settings missing, so it falls back to "this device only". The preview has these settings, which is why check-in worked there. The exact reason the live site lacks them is not yet confirmed (most likely the live copy was published before the settings were attached, or they need re-attaching).

"Removing the helper from startup" was a separate tidy-up: a sign-in piece that runs on every page but isn't used by check-in. It is not the main fix.

## Plan
1. Re-attach the backend settings for the live site (safe, no keys change).
2. Make the check-in server code read only what it needs, and remove the unused sign-in helper from startup so it can't raise this error.
3. Replace the technical text with a plain message that also says why, e.g. "Can't reach the shared list — the site's server isn't connected to the backend. Retrying…", "…no internet connection", or "…the server didn't answer", and log the full detail for me.
4. You publish once; then I verify on ran1.app with two separate browser sessions using the same code that both names appear in the same room.

## Technical details
- Run `supabase--rebind_secrets`; check server-function logs for the live error.
- `src/start.ts`: drop `attachSupabaseAuth` (no protected server functions).
- `RoomColleagues.tsx` `PresenceStatus`: friendly copy, raw error to console only.
