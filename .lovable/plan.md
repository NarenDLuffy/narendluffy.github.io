# Fix and verify company room check-in

## What I found
- The shared check-in list in the backend has only one old test entry (from August). None of tonight's check-ins (laptop or phone) arrived there, so each device only saw its own check-in.
- The backend table itself is set up correctly.
- The app hides failures: if one save or fetch fails even once, that device quietly switches to "this device only" for the rest of the visit and never tries the shared list again. Nothing tells you this happened.
- The exact reason the save failed is not confirmed yet. The first step is to reproduce it and read the error.

## Plan
1. Reproduce: run two separate browser sessions against the app with the same company code, check both into one room, and capture the exact error from the save.
2. Fix the root cause found in step 1 (most likely the server side of the save, e.g. the code-hashing step on the hosting runtime).
3. Stop the silent fallback: keep retrying the shared list on every refresh instead of giving up for good.
4. Show the status on the Company page and room page: "Shared with your company" or "Not connected - only visible on this device", plus the error if a check-in failed to save.
5. Make sure both devices are truly in the same group: show the active company code (lightly masked) so you can confirm laptop and phone use the same one (codes ignore capitals and extra spaces).
6. Refresh the room list right after check-in and every 20 seconds (already the case), and when the page comes back into view.
7. Company code capitals: keep ignoring capitals and extra spaces (so "Ericsson" and "ericsson" join the same group), since a capital-letter typo on a phone would silently split colleagues. Say so under the code box.
8. Tapping a schedule block: the detail sheet shows "Colleagues in this room" with everyone from your company checked into that block's room, plus an "I'm in this room" / "Check out" button. Shows a prompt to join on the Company page if you have no code.

## Verification
- Two independent browser sessions, same code, same room: each sees both names within 20 seconds.
- Different codes: neither sees the other.
- Check out on one: disappears on the other.
- Different meeting: no leftover check-ins.
- Confirm the rows appear in and disappear from the backend.

## Technical details
- Files: `src/services/remotePresenceStore.ts` (drop sticky `remoteAvailable`, surface last error), `src/lib/presence.server.ts` (replace `crypto.createHash` with Web Crypto `crypto.subtle.digest` if that is the failure), `src/hooks/useCompanyPresence.ts` (expose status, visibilitychange refresh), `src/routes/company.tsx` and `src/routes/rooms.$roomId.tsx` (status line).
- Use Playwright with two contexts plus server-function logs to confirm.
