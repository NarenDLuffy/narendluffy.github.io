# Reduce load on 3GPP servers and on the app

## Goal
Load on 3GPP and on our backend should stay the same whether 5 or 500 delegates use the app. Every number shown should stay as fresh as it is today, or within 1–2 minutes of it.

## What causes load today
- **Drafts page:** every open copy rescans about 200 folder pages on 3GPP once a minute, even in the background. Its 30-second memory isn't shared between users.
- **Room presence:** every open app asks our backend every 20 seconds.
- **Backup alerts:** every open app asks every 15 seconds.
- **Schedule and Drafts snapshots:** re-downloaded every 5 minutes. Meeting info every 15.
- **Background jobs:** Drafts every 5 minutes on weekdays, Schedule every 5 minutes plus the watcher. This is fine, but it runs at full speed in weeks with no meeting.

## Changes

### 1. One shared Drafts scan for everyone (biggest win)
- A backend job scans the live Drafts tree once for each working group and saves the result in the database.
- It runs every 2 minutes on meeting days, every 15 minutes in the 3 days before and after, and every hour otherwise.
- It only scans groups that have a meeting in that window.
- Phones only read that saved result. They never scan 3GPP themselves.
- If the saved result is more than 2 minutes old, one user's visit can trigger a single new scan. A lock makes sure two scans never run at once.

### 2. Gentler scanning
- Ask 3GPP for a folder only if it changed, where the server supports that. Unchanged folders cost almost nothing.
- Recheck busy folders (the latest Inbox and Round folders) every time. Recheck quiet ones every 4th time.
- Keep the 240-page limit and 6 parallel requests, and add a short pause between batches.

### 3. Phones stop working when nobody is looking
- Pause all refreshes when the tab is hidden or the screen is off. Refresh once when the user comes back.
- New Drafts refresh: every 60 seconds while the page is open, reading only our saved copy.
- Schedule: every 5 minutes on meeting days, 30 minutes otherwise.

### 4. Room presence and backup alerts: push instead of asking
- Use live updates from the backend for check-ins and alerts, so phones stop asking every 15–20 seconds.
- Keep a slow fallback check (every 2 minutes) only if the live connection drops.

### 5. Background jobs follow the meeting calendar
- Drafts and Schedule jobs run at full speed only during the meeting window (the week, plus a day on each side). Outside it they run hourly or a few times a day.
- The schedule watcher keeps its 5-minute check, which only matters in meeting week.
- The Drafts GitHub job stops scanning live folders that the shared scan already covers. It only writes the daily saved snapshot.

### 6. Faster, cheaper data files
- Serve schedule and drafts files with short shared caching (about 60 seconds), so many users share one download.

## Expected effect
```text
                        today (30 users)        after (any number of users)
3GPP Drafts pages/min   up to ~6,000            ~100 (one scan per 2 min, mostly "unchanged")
Backend presence calls  ~150/min                near zero (live updates)
Hidden/background tabs  full load               nothing
```

## Technical details
- New table `drafts_live_scan` (group, meeting slug, result JSON, scanned_at, lock_until). Public read access, written only by the server.
- New `/api/public/jobs/drafts-scan` route on a managed schedule (every 2 minutes). The handler checks `meetingPhase` and does nothing when the group is out of its window. It reuses `crawlSync` and `walkListing`.
- `loadDraftsLive` reads the table, with a stale-triggered refresh behind the lock. Drop `refetchIntervalInBackground`.
- Conditional requests use `If-Modified-Since`/ETag, kept per folder in the scan record. Fall back to a full read when the server ignores them.
- Presence and alerts move to the realtime doorbell pattern, replacing `setInterval` polling in `useCompanyPresence` and `useCompanyAlerts`.
- Pause refreshes with React Query's `refetchIntervalInBackground: false` plus a `visibilitychange` guard on the custom intervals.
- Slow the GitHub cron schedules outside meeting windows using phase checks at job start. The cron entries themselves stay put so they can't drift.
- Add tests: phase-based scan interval, lock prevents double scan, hidden tab does not poll.
- Venue server (10.10.10.10) is untouched: it stays switched off.
