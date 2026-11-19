# RAN3 support — same app, third working group

Add RAN3 to the RAN1/RAN2 switch. Schedule, Now, My agenda, Rooms, check-in, alerts, Drafts and Help all follow the switch exactly like RAN2 does today. Only the schedule reading is new.

## What the RAN3 sources look like (checked on RAN3#134, Calgary)

**Online / main session** — Chairs_Notes folder, files like `RAN3_134_agenda_20261119_0921.docx` (timestamped, several per day, some with `_L` suffix). The last weekday table in the file:

```text
        | Monday               | Tuesday            | ...
08:00   | 0900 START OF MEETING| Offline*           |
09:00   | Org: AI 1-8          | 6G SI: AI 10.1,10.3.2
10:30~  | Coffee Break         | Coffee Break  (+ "6G Offline (CB#9)" in same cell)
(blank) | Corrections: AI 9    | 6G SI: AI 10.2     |   <- time bounded by the breaks
13:00~  | Lunch Break          | ...
```

**Offline** — `Offline_meeting_room/RAN3 offline discussion_ver_NN.xlsx`, one sheet per day ("Nov16 Mon"), rows of 30-minute slots: Time Slot | Topic (e.g. "R20 SON/MDT [AI:11.2] (GTW)") | Moderator.

Both exist under the meeting folder before the week and under Meetings Sync RAN3 during it; the same date rule as RAN1/RAN2 decides which folder is read.

## What delegates will see

- RAN3 in the group switch; Schedule shows a **Main** room (online, from chair notes) and one offline room per room tag found in the spreadsheet (e.g. "GTW"), or a single "Offline" room when no tag is given.
- Session titles like "6G SI: AI 10.1, 10.3.2" are linked to agenda items 10.1 and 10.3.2, so starring items in My agenda filters the schedule. "AI 11X / 12L / 14X" style codes map to their parent item.
- Back-to-back offline half-hour slots with the same topic and moderator merge into one block (e.g. SON/MDT 11:30–13:00), with the moderator shown.
- Drafts for RAN3 come from the RAN3 Inbox drafts folders, same as RAN2.
- Help / How to use mentions RAN3 and where its schedule comes from.

## Rules (no invented times)

- Main-session times come only from the table: stated times in the first column, and blank-time rows bounded by the breaks above and below. A row whose start or end cannot be bounded is reported as a problem and blocks the publish.
- Break cells with an extra line ("Coffee Break / 6G Offline (CB#9)") become a break in Main plus an offline block in that slot.
- Struck-through / deleted text is ignored (existing reader).
- Newest file wins: chair notes ordered by the date-time in the file name; spreadsheet by `ver_NN`. Older-revision protection applies as for RAN1/RAN2.
- Overlaps inside one room block the publish.

## Steps

1. Register RAN3 as a working group (portal body, slug `ran3`, Sync folder RAN3, new schedule style "chair_notes_plus_sheet").
2. Source discovery: pick newest chair-notes DOCX and newest offline XLSX for the meeting number (+bis suffix), following the meeting-phase folder rule.
3. New reader `ingestion/ran3_schedule.py`: weekday table from the DOCX → Main blocks; XLSX sheets → offline blocks; agenda codes from "AI x" / "[AI:x]".
4. Agenda list for My agenda from the chair-notes agenda headings (the same file).
5. Plug into the existing publish, validation, health check and GitHub workflows (schedule + drafts, plus the Sync watcher).
6. Frontend: add RAN3 to the switch and group lists; Help text.
7. Tests from the real RAN3#134 table and sheet (break-bounded times, CB line in break cell, slot merging, AI code mapping), then build RAN3#134 and check it in the browser.

## Technical details

- `ingestion/groups.py`: `WorkingGroup("RAN3", <tb_id>, "ran3", "RAN3", "chair_notes_plus_sheet")` (tb_id looked up from the portal).
- XLSX read with `openpyxl` (add to `ingestion/requirements.txt`); sheet date from sheet name + meeting dates.
- Reuse `docx_active_text` for runs, `validator`, `live.coverage_gaps`, `revision_diff` family keys (family = "ran3-chair-notes", "ran3-offline").
- RAN3-specific topic aliases (if needed) live in a separate `ran3_topics.py`; RAN1/RAN2 logic unchanged.
- Record the RAN3 rule in `ingestion/AGENTS.md`; update the meeting-refresh skill.
