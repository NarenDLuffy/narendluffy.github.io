# My agenda: reorder, durations, and auto-linking named topics to agenda numbers

## 1. Reorder the My agenda page
New order, top to bottom:
1. My timeline (followed sessions by day, with Export .ics / Clear)
2. Draft activity for my items
3. Follow agenda items (the full chip list)

When nothing is followed yet, the empty-state hint ("Star agenda items below…") stays at the top and points down to the list.

## 2. Show duration on each timeline row
Each row shows the start, end and length, e.g. `10:00–11:00 · 1h` or `14:30–16:30 · 2h`, `11:30–12:15 · 45 min`. The start time stays bold; the end and length are smaller and muted so the row stays compact on phones.

## 3. Link name-only topics to their agenda number
Problem: some schedule blocks only say a topic name ("R20 AI/ML", "AI/ML", "MIMO", "A-IoT Phase2", "NTN-NR") with no agenda number, so following 9.1 misses them. In RAN1#126bis, 57 blocks have no agenda number (some are breaks/opening, which stay unlinked).

Fix, done when the schedule is built from the documents:
- For every block without an agenda number, compare its topic words against the agenda item names from the latest chair notes (already used for agenda titles), e.g. 9.1 "Artificial Intelligence (AI)/Machine Learning (ML) for NR air interface…", 9.2 "NR MIMO Phase 6", 9.3 "Ambient IoT … Phase 2", 9.4/9.5 NTN.
- Release hints narrow the search: "R20" means the Release 20 section (9.x); "6GR" means the 6G section (10.x). Without a hint, prefer the current-release section the meeting is working on and only link when exactly one agenda item matches.
- Matching uses the agenda title words plus their standard short forms found in the title itself (AI/ML, MIMO, A-IoT/Ambient IoT, NTN), so nothing is hard-coded per meeting.
- If the match is unclear (two equal candidates), the block is left unlinked rather than guessed.
- Linked blocks are marked as "linked from topic name" so the session details show the agenda number came from the chair notes, not the schedule cell.

Result: following 9.1 in My agenda includes the "R20 AI/ML" blocks, and the Timetable's "My agenda items" filter highlights them too.

After the change, rebuild only the current meeting's data (RAN1#126bis), confirm the AI/ML blocks now carry 9.1, and check the My agenda page in the preview.

## Technical details
- `src/routes/agenda.tsx`: move sections; add `endTime` and a `formatDuration(minutesOf(end) - minutesOf(start))` helper (in `scheduleService.ts`).
- New `ingestion/topic_agenda_mapper.py`: builds a keyword index from `agenda.json` titles (tokens + parenthesised/abbreviated forms), scores topic tokens, applies R20/6GR section scope, returns a single code or None. Called in `canonical_schedule.py` for session/plenary blocks with empty `agendaItems`; sets `agendaItems=[code]` and `derivation.agendaSource="topic-name"`.
- Unit tests in `ingestion/tests/` for "R20 AI/ML"→9.1, "MIMO" with R20→9.2, "A-IoT Phase2"→9.3, ambiguous→None, breaks untouched.
- Record the rule in `AGENTS.md`.
