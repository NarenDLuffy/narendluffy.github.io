# Keep the meeting's remote server address visible and fixable

## What this fixes

The FTP login (username and password) is the same at every meeting, so those two entries are added on GitHub once and never touched again. Only the **host name** changes each meeting, and that is entered in the app, not on GitHub.

Two problems with the host entry today:

1. Once someone types it, the card disappears for everyone. Nobody can see which address is currently in force, so there is no way to tell whether the meeting's documents are being read from the remote server at all.
2. The first answer is kept forever and later answers are ignored. If the first person types the wrong address, or the venue changes it mid-week, nothing can correct it — the app keeps knocking on the wrong door and quietly falls back to the other sources.

## What you will see

On the **Drafts** page, under the meeting banner, a small line:

```text
Remote server: RAN-Seoul.3gpp.org        [ Change ]
```

- When nobody has entered one yet, it reads `Remote server: not set` and the field is open, as today.
- **Change** opens the same box, you type the new address, and saving replaces it for everyone — no waiting for the first person.
- If you pressed **Skip** on this device earlier, a `Set remote server` link brings the box back instead of the prompt staying buried.
- Nothing moves on GitHub. The login stays where you put it.

**How to Use** gains one plain sentence: the login is saved once by the app owner on GitHub; the address is entered once per meeting here, and only the address changes.

## Technical detail

- `src/lib/meetingSettings.functions.ts`: add an explicit overwrite path — `updateMeetingFtpHost` (or a `replace: true` flag on `setMeetingFtpHost`) that writes the new host even when one is stored. The passive first-answer-wins behaviour stays for the ask-card, so two people opening the box at once still cannot fight over it. Same host validation as now.
- `src/components/RemoteFtpHostCard.tsx`: stop returning `null` when a host exists. Render the compact status row in every state, keep the ask form for the empty case, and keep the **Change** form for the filled case. The per-meeting skip flag in local storage is cleared when the owner opens the box from the status row, so a skipped device is never stuck.
- `src/routes/drafts.index.tsx`: the card stays where it is (current meeting, not completed) — no new placement.
- `src/routes/help.tsx`: the one-sentence note above, under the drafts/night-time section that already exists.

## Checks

- `bunx tsgo --noEmit` clean.
- Preview on `/drafts`: address shows, **Change** replaces it, the new value survives a reload, and `Set remote server` reappears after a Skip.
- After a real change, the next updater run reads the new address (visible in the run log or by documents arriving that the other sources don't have).
