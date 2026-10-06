# How to use RAN1 Live

A quick tour for delegates. Nothing to install, no account, no login — open the
link on your phone and it works. Add it to your home screen for a full-screen,
app-like experience (Safari: Share → Add to Home Screen; Chrome: ⋮ → Install).

> Unofficial tool. Schedule data is generated automatically from 3GPP meeting
> documents and may contain errors — always confirm against the chair notes.

---

## The tabs

### Now
What is running right this minute, in meeting-local time. Each card shows the
session, the room, the agenda items being covered and how far through it is.
Use this when you walk out of a session and need to know where to go next.

- **Refresh** reloads the latest published schedule right away and shows when
  the schedule was last rebuilt.
- **FL deadline badges** appear here when a deadline you set is due soon.

### Schedule
The full week as a timetable grid, one column per parallel track, every day
drawn from 08:30 to 19:30 so the days line up.

- Each room has its own colour, used on the timetable, the Rooms tab and the
  room pages.
- Room names show the session label in brackets where the chairs' documents
  give one, e.g. "1.1 Himalaya (RAN1 Brk2)".
- The agenda filter highlights matching blocks and dims the rest; tick
  **Hide others** to hide them completely. Breaks and lunch always stay
  visible.
- Tap any block to see the full agenda titles (e.g. "10.5.5 — Other physical
  channels and signals") with the per-item minute breakdown.
- Coffee and lunch bands are shown across the full width.
- Search and agenda filters narrow the grid to the topics you care about.
- The star on a block adds that session to **My agenda**.
- **Refresh** pulls the newest schedule immediately and shows when it was last
  rebuilt.

### My agenda
Everything you starred, in chronological order, plus a calendar export.
Tap **Export .ics** to drop your personal selection into Outlook/Google/Apple
Calendar for the week.

- Exported times use the meeting city's time zone (daylight-saving handled),
  so 09:00 in Prague shows as 09:00 in Prague in your calendar.
- Events include the room with its session label, full agenda names, and
  30-minute alarms for any FL deadlines you set.

### FL deadlines
Add a deadline yourself per agenda item — tap **Deadline** in the block
details sheet (e.g. "FL summary #1 due Tue 18:00").

- Reminders show as a badge on **Now** and as calendar alarms in the .ics
  export.
- The RAN1 email reflector is members-only behind an ETSI login, so deadlines
  cannot be read automatically — they are manual and stay on your own device.

### Drafts
Live tracking of the meeting's working documents.

- The tree mirrors the actual `Inbox/` directory as discovered on the server —
  no hard-coded folder names, so it works for every meeting.
- **All activity** shows every new or updated file.
- **My items** shows only files under agenda items you bookmarked or followed.
- Unread counts appear on the tab and on each folder; opening an item clears it.
- The source line tells you where the data came from — **Venue** (10.10.10.10,
  used when you are on the meeting Wi-Fi), **Sync** (the 3GPP SYNC mirror), or
  **Published** (the last snapshot built by the pipeline). The same file arriving
  on several servers is de-duplicated into one entry.
- It re-checks about every 60 seconds; **Refresh now** forces an immediate
  re-scan and tells you exactly how many files were new or updated.

### Rooms
Only the rooms in use at the current meeting, each with its own colour and
session label. Open a room to see its whole day. If your colleagues use the
Company tab, you can also see who is currently in which room.

### Company (optional)
Voluntary, account-free presence sharing with your colleagues: pick a shared
group code, set a display name, and check in to a room. It expires by itself
after two hours, is scoped to one meeting, and never uses your location.
Everything you enter stays on your own device unless a shared backend is
explicitly enabled.

### Changes
A diff feed: sessions that moved, rooms that changed, agenda items added or
dropped since the previous version of the schedule documents.

### Meetings
Switch between meetings. RAN1 Live discovers all meetings from the official 3GPP
portal, so past meetings stay browsable as an archive and the next meeting
appears automatically — the current one is selected for you by default.

---

## Good to know

- **Keeping up to date**: the schedule and drafts are rebuilt from the newest
  3GPP documents every 5 minutes during meeting hours, so new room names,
  session labels and document revisions appear on their own — no reinstall, no
  republish. Tap **Refresh** to pull the latest immediately.
- **Offline**: the last loaded schedule is cached, so the app still opens in a
  basement meeting room with no signal. A banner tells you the data is stale.
- **Your data**: bookmarks, follows, read state, deadlines, display name and
  presence live only in your browser's storage on your device. Clearing site
  data resets them.
- **Times** are always shown in the meeting's local time zone, not your phone's.
- **Venue mode**: direct reading of the 10.10.10.10 meeting-local server is
  currently switched off; drafts and the schedule come from the public 3GPP
  meeting-sync source. The code is kept for the future if the venue server
  supports HTTPS.
- **Limitations**: the schedule is parsed from chair/sub-chair DOCX files, so a
  last-minute change made verbally in the room will not appear until an updated
  document is uploaded.

Questions, wrong sessions, missing rooms? Send a screenshot — parser fixes are
usually quick.
