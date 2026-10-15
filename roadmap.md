# Roadmap

- [x] Friday v05: preserve room identity when shading is omitted; Main 11:00–13:00 is Sweep; rebuild and audit all chair files (47 tests, no mismatches)
- [ ] GitHub main must receive the rebuilt Friday schedule; live preview still reads its older copy first

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
