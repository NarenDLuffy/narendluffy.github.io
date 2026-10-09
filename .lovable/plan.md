# Why check-in says "Not connected — Missing Supabase environment variables"

## Cause
The message comes from the app's sign-in helper, which runs on every page and needs the backend address. That address is only included when the app is built and hosted by Lovable (ran1.app, preview). The copy built by GitHub (narendluffy.github.io / 3gpplive.net) is built without it, and it also has no server at all, so shared check-in can never work there. Company check-in does not use sign-in, so this helper isn't needed.

## Fix
1. Remove the unused sign-in helper from app startup, so the static copy no longer crashes check-in with this technical error.
2. On copies without a server (GitHub Pages), replace the orange error with a plain message: "Shared check-in only works on ran1.app. Check-ins here are only on this device." with a link to ran1.app.
3. On ran1.app, keep the current status line ("Shared with your company" / "Not connected… Retrying").

## Verify
- Preview: two separate browser sessions with the same code see each other in the same room.
- Static build: the plain message shows, no technical error.

## Technical details
- `src/start.ts`: drop `attachSupabaseAuth` from `functionMiddleware` (no protected server functions exist).
- `src/services/remotePresenceStore.ts` / `RoomColleagues.tsx`: detect static hosting (existing GitHub Pages build flag) and show the friendly message instead of calling server functions.
