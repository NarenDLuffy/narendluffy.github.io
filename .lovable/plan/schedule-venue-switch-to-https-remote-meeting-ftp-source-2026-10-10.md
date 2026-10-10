# Schedule venue switch to HTTPS + remote meeting FTP source

## 1. Schedule page "Use meeting-local server" (not changed yet)
The previous change covered Drafts only. The Schedule page switch still defaults to `http://10.10.10.10/...`, which ran1.app (secure page) can never read.

- Default address becomes `https://10.10.10.10/ftp/RAN/RAN1/Inbox/`; if that fails, try the `http://` form (only works on a plain-HTTP page). Same freshness rule as today (only adopted when genuinely newer).
- Devices that saved the old default http address get upgraded to the new default automatically; a custom address someone typed stays as is.
- The panel shows the HTTPS caveat in one short line (certificate must be valid for 10.10.10.10, otherwise it silently falls back).

## 2. Remote meeting FTP (e.g. RAN-Maastricht.3gpp.org)
Browsers and the app cannot speak FTP, and this server is only reachable from outside the 3GPP network — which is exactly where GitHub Actions runs. So it becomes an extra source for the automatic 5-minute refresh, not an in-app probe.

- Each meeting gets a `remoteFtpHost` (e.g. `RAN-Maastricht.3gpp.org`). No guessing — names vary. While it's empty for the current meeting, the Drafts page shows a small card asking "Remote FTP host for this meeting?" with a text box and a Skip button (skip hides it on that device only). Once any user saves a host, it's stored once in the backend for that meeting and the card disappears for everyone; the GitHub Action reads it from there. Until then, this source is simply skipped.
- Username/password stored as GitHub repository secrets (`MEETING_FTP_USER`, `MEETING_FTP_PASS`), not in code — you'd add them once in GitHub settings (same across meetings).
- Used only during the meeting week (start −1 day to end +1 day), in addition to the Sync folder and the meeting folder; same rules as today: meeting-number/bis filename check, 14-day age cutoff, freshest version wins, duplicates merged.
- Applies to both schedule files and drafts the Action collects. Works day and night; at night it simply keeps things fresh when the venue server isn't reachable from your room.

## 3. How to Use
Add one bullet: during the meeting week the app also refreshes from the meeting's remote FTP server (outside the venue network), and the HTTPS venue caveat now applies to the Schedule switch too.

## Technical details
- `src/services/localSource.ts`: `DEFAULT_LOCAL_BASE` → https; transport tries https then http twin; migrate stored legacy default in `getLocalSourceSettings`.
- `src/components/SourcePanel.tsx`: caveat text.
- `src/types/meeting.ts` + meeting data: optional `remoteFtpHost`.
- `ingestion/`: new `remote_ftp.py` using `ftplib` (passive, TLS attempted then plain, short timeout), listing the Inbox tree recursively and feeding discovered files into existing discovery/`_belongs_to_meeting` pipeline; gated by meeting-week window and presence of secrets.
- Workflows: pass the two secrets as env vars to schedule and drafts jobs.

## Open question
Which folder on the remote FTP holds the Inbox? Resolved: same layout as Meetings Sync — crawl `RAN1/Inbox/` recursively.
