# RAN1 Live — Colleague Testing Checklist

Use this checklist to walk through the app before or during RAN1#126 and tell us what works, what breaks, and what is missing. Copy it into an issue, email, or Slack thread and check the boxes as you go.

**Site:** https://ran1.app

---

## How to report

For anything that feels off, please include:

1. The page you were on.
2. What you tapped/clicked.
3. What you expected vs. what happened.
4. A screenshot if possible.
5. Your browser and phone/OS.

---

## 1. First impression

- [ ] Open https://ran1.app on the device you will carry during the meeting (phone is ideal).
- [ ] Add it to your home screen / install it as an app:
  - **iPhone Safari:** Share → Add to Home Screen.
  - **Android Chrome:** ⋮ → Install app / Add to Home Screen.
- [ ] Confirm the app icon and name on your home screen look right.
- [ ] Confirm the tab/app icon shows **3GPP** instead of a Lovable logo.

**Feedback:** Does the home-screen install feel like a real app? Is the first load fast enough?

---

## 2. Meeting switcher

- [ ] The header should already show the current or upcoming RAN1 meeting.
- [ ] Tap the meeting name in the header to open `/meetings`.
- [ ] Pick a different meeting (e.g. RAN1#125 or RAN1#127) and confirm the schedule/drafts/rooms update.
- [ ] Switch back to RAN1#126 / the auto-selected meeting.

**Feedback:** Is the current-meeting guess correct? Is switching obvious?

---

## 3. Now page (`/`)

- [ ] The clock in the header shows the meeting's local time.
- [ ] "Happening now" lists sessions that are running at this exact time.
- [ ] "Starting next" lists the next sessions in order.
- [ ] Tap any session card and confirm you see the agenda-item breakdown.
- [ ] Scroll down and check the "Draft activity" and "Latest changes" highlights.

**Feedback:** When you are between sessions, is it obvious where to go next?

---

## 4. Schedule (`/schedule`)

- [ ] The grid shows every meeting day from **08:30 to 19:30**.
- [ ] Parallel tracks are clearly separated.
- [ ] Shared rooms (e.g. `0.6/0.7 Madrid/Lisbon`) are shown once, not duplicated.
- [ ] Coffee and lunch breaks run full width across the grid.
- [ ] Try the search/filter controls.
- [ ] Tap a session block and check the timed sub-slots (e.g. `(30 min)` per agenda item).
- [ ] Star a session and confirm the star stays filled.

**Feedback:** Is every agenda item you expect shown? Any missing or duplicate sessions? Is the room name clear?

---

## 5. My agenda (`/agenda`)

- [ ] Starred sessions appear here in chronological order.
- [ ] Tap **Export .ics**, download the file, and import it into Outlook / Google Calendar / Apple Calendar.
- [ ] Confirm the events land on the right days and times in your calendar.
- [ ] Remove a star from one session and confirm it disappears from My agenda.

**Feedback:** Does the ICS export work with the calendar app you actually use?

---

## 6. Drafts (`/drafts`)

- [ ] The page shows a source line such as **Venue**, **Sync**, or **Published**.
- [ ] Press **Refresh now** and wait for the status line (e.g. "5 new, 2 updated").
- [ ] Toggle between **My items** and **All agenda items**.
- [ ] Follow an agenda item and confirm it appears under **My items**.
- [ ] Open a folder and confirm the breadcrumb/path matches the real 3GPP Inbox tree.
- [ ] Confirm unread badges appear and clear after you open a folder.
- [ ] Press **Mark all read** and confirm badges disappear.

**Feedback:** Are the latest venue documents visible? Any duplicates? Is the folder tree easy to understand?

---

## 7. Rooms (`/rooms`)

- [ ] Every physical room used during the week is listed.
- [ ] Tap a room and verify its day schedule.
- [ ] Confirm the room name matches what you see on the meeting signs.

**Feedback:** Is any room missing or misnamed?

---

## 8. Company presence (`/company`)

- [ ] Enter a shared group code (e.g. your company name) and a display name.
- [ ] Check in to a room.
- [ ] Ask a colleague to use the same group code and confirm you see each other.
- [ ] Wait ~2 hours (or check the expiry note) and confirm presence times out.

**Feedback:** Would you actually use this? Is the group-code sharing too awkward?

---

## 9. Changes (`/changes`)

- [ ] Open the page and review any schedule diffs.
- [ ] Confirm each change is described clearly (moved session, room change, added/dropped item).

**Feedback:** Are the changes useful, or is the page just noise?

---

## 10. Offline / resilience

- [ ] Load the site once while online.
- [ ] Turn on airplane mode or disable Wi-Fi.
- [ ] Reload the page.
- [ ] Confirm a stale/cached banner appears and the last schedule is still usable.
- [ ] Turn Wi-Fi back on and confirm fresh data returns.

**Feedback:** Did you get stuck anywhere with no signal?

---

## 11. Help & admin

- [ ] Open `/help` and read "How to use RAN1 Live".
- [ ] Confirm the new **Share this checklist** link opens this document.
- [ ] Open `/admin` and confirm the ingestion status is readable.

**Feedback:** Is anything in the help page still confusing?

---

## General feedback

Please answer these even if everything above worked:

1. **One thing you would use every day during the meeting:**
2. **One thing that confused you on first use:**
3. **One feature missing before you would rely on this app:**
4. **Any data errors?** (wrong time, wrong room, missing session, duplicate session, wrong agenda mapping)
5. **Anything you would not want to see in a public URL?**

---

Thank you! Send the completed checklist or screenshots to whoever shared this link with you.
