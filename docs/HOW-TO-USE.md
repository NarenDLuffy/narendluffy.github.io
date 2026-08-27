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

### Schedule
The full week as a timetable grid, one column per parallel track, every day
drawn from 08:30 to 19:30 so the days line up.

- Tap any block to see the agenda-item breakdown with per-item minutes.
- Coffee and lunch bands are shown across the full width.
- Search and agenda filters narrow the grid to the topics you care about.
- The star on a block adds that session to **My agenda**.

### My agenda
Everything you starred, in chronological order, plus a calendar export.
Tap **Export .ics** to drop your personal selection into Outlook/Google/Apple
Calendar for the week.

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

### Venue mode (on meeting Wi-Fi)
When you are in the meeting venue and connected to the meeting Wi-Fi, the
fastest source is the local server at `10.10.10.10`. Browsers refuse to let an
HTTPS page read an HTTP server, so the secure main site cannot do this directly.

If the app detects it is blocked, it shows a banner offering to open **venue
mode** on a plain-HTTP copy of the same app. Venue mode can read `10.10.10.10`
directly and therefore gets the freshest drafts and any meeting-local schedule
updates. Tap **Open venue mode**, and your bookmarks, follows and read state are
carried over. When you leave the venue, use the link back to the secure site.

If you never see the banner, the app is probably falling back to the public
SYNC mirror, which is fine but may be a few minutes behind.

### Rooms
Every physical room used this week and what is scheduled in it. Open a room to
see its whole day. If your colleagues use the Company tab, you can also see who
is currently in which room.

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

- **Offline**: the last loaded schedule is cached, so the app still opens in a
  basement meeting room with no signal. A banner tells you the data is stale.
- **Your data**: bookmarks, follows, read state, display name and presence live
  only in your browser's storage on your device. Clearing site data resets them.
- **Times** are always shown in the meeting's local time zone, not your phone's.
- **Venue mode**: the plain-HTTP venue twin is only for use on the meeting LAN.
  It does not support account-based features; switch back to the secure site for
  those.
- **Limitations**: the schedule is parsed from chair/sub-chair DOCX files, so a
  last-minute change made verbally in the room will not appear until an updated
  document is uploaded.

Questions, wrong sessions, missing rooms? Send a screenshot — parser fixes are
usually quick.
