# Roadmap

- [x] Push notifications for "colleague needed" alerts
- [x] Update "How to Use" (help.tsx) with summon alerts + notifications
- [x] Drafts source cleanup: live server is the truth during the meeting week (old archive files hidden, no duplicate rows)
- [x] GitHub secrets MEETING_FTP_USER / MEETING_FTP_PASS added
- [x] Pipeline health record + Ingestion status panel + daily "Verify data" job
- [x] Schedule: Hiroki v05 picked up; minutes that don't add up are never placed (Sensing "(6)")
- [x] Schedule: Wednesday Tamna BC gaps fixed (continuation rows read twice); any gap a document fills now blocks the publish
- [x] Verify data: missing remote address is a note; stale data fails and restarts the refresh jobs; Node 24 action versions
- [x] Four meeting-week skills active
- [x] One folder rule for timetable + drafts; table cell sanity checks; pictures on refused runs
- [x] Normalize wildcard parent matching, rebuild RAN1#126bis, and verify Hiroki's four stated child timings
- [x] All chair schedules: read range minutes, bare agenda numbers, multi-item lines; granularity check + audit + skill
- [ ] User: enter this meeting's remote FTP host (RAN-<city>.3gpp.org) on the Drafts page
- [ ] User: enable notifications on each device and test a summon alert end-to-end
- [ ] User: confirm branch-level draft activity shows under a followed sub-item (e.g. 10.4.1)
- [x] Drafts page shows the saved copy at once; live folders checked in the background, 6 at a time
- [x] Remote FTP host accepts underscores (jeju_icc.3gpp.org)
- [x] Timetable rebuilt from chair schedule v04; table disagreements shown on the blocks; Verify data no longer fails on them
- [ ] User: create a GitHub token so the 5-minute backend watcher can start the timetable update (blocked on token)
- [x] Latest-change rule: the table a chair edited most recently wins over untouched copies (Thu Room 201 10.5.3.4, Friday grid order)
- [x] Voting question answered: file counts only break ties between equally fresh claims
- [x] Main online/offline grid controls every room's times and lunch; other files contribute detail only
- [x] Fix Drafts crawl server error and prevent a failed crawl from blanking the page
- [x] Keep NTN-NR inside Room 225-226's single Wednesday timeline, not as an overlapping block
- [x] Verify Wednesday BMO 221 against Hiroki's DOCX and daily PDF: both state only Sensing (90); no other room's split copied
- [x] Preserve Hiroki hh7's Friday Room 214-215 5/10/75 split and make the granularity audit catch complete chair retilings

- [x] RAN1/RAN2 working-group switch: schedule, Now, agenda, rooms, Drafts (Inbox/Drafts), watcher
- [x] App description and How to Use explain RAN1 and RAN2 support

## Load reduction + new groups (approved plan)
- [x] Shared Drafts scan for everyone (one 3GPP crawl per tree per ~90 s, database lock)
- [x] Hidden tabs/locked phones stop refreshing Drafts, presence and alerts; slower polling
- [x] Working-group dropdown (new groups listed as coming soon)
- [x] Credit to Duckhyun Bae (karlla1220) on home page and Help
- [x] Presence/alerts pushed live instead of polled (live ping, 2-min fallback poll)
- [x] "Only if changed" requests + shared download cache for ingestion (jobs already scan by meeting phase)
- [x] RAN Plenary schedule reader (Main + Breakout lanes, breaks, meetings during breaks; RAN#113 built)
- [x] RAN4 schedule slides reader (RAN4#119–#121 built; topic list links agenda items and Drafts folders)
- [x] SA2 session plan reader (SA2#167–#178 built)
- [x] SA1 chair grid reader (SA1#116 built)
- [x] Drafts Activity view (threads, versions, Summary #N milestones)
