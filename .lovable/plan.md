# Shorten colleague checklist into a Teams message

## Goal
Turn the current `docs/COLLEAGUE-CHECKLIST.md` into a concise, copy-paste-ready message for Microsoft Teams that colleagues can actually read and reply to.

## Deliverables
1. Create `docs/COLLEAGUE-CHECKLIST-TEAMS.md` — a short Teams-friendly version (under 30 lines).
2. Keep the full detailed checklist at `docs/COLLEAGUE-CHECKLIST.md` as the canonical reference.
3. Update the in-app `/help` page to offer both:
   - "Copy short Teams message"
   - "Open full checklist"
4. Publish the update so the new link works on `ran1.app`.

## Proposed Teams message structure
- One-line intro + site link.
- 5 quick checks (not 11 sections).
- 3 specific feedback questions.
- Total length: small enough to paste into Teams without scrolling.

## Files to change
- `docs/COLLEAGUE-CHECKLIST-TEAMS.md` (new)
- `public/COLLEAGUE-CHECKLIST-TEAMS.md` (new, for serving)
- `src/routes/help.tsx` (add short-message link/button)
- Re-publish via Lovable so `ran1.app/COLLEAGUE-CHECKLIST-TEAMS.md` resolves.

## Open question
Should the Teams message replace the full checklist link in `/help`, or should both be shown? Default plan: show both, with the short one highlighted first.