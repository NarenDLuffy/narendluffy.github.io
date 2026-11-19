# RAN3 comebacks (CB) linking agenda items to Drafts folders

## What it does for RAN3 users
- Each agenda item in My agenda shows its comebacks, e.g. 10.5.1 AI/ML use cases -> "CB # 6GAIML1_Usecase".
- Starring an agenda item also shows that comeback's Drafts folder (Inbox/Drafts/CB # 6GAIML1_Usecase) in the Drafts tab, even though the folder name has no agenda number.
- Each comeback has an **Open** or **Closed** badge. Closed means the chair removed "CB:" from the line in his notes. Closed comebacks stay visible, greyed out and listed last, so their drafts can still be found.
- Schedule blocks that name a comeback ("6G Offline (CB#9)") get that comeback's agenda item, so they appear when you star it.
- RAN1 and RAN2 do not change.

## What the chair notes show (checked in RAN3_134_agenda_20261119_1430.docx)
- Comebacks are pink (FF00FF) paragraphs "CB: # <n>_<Name>" under an agenda item's heading (for example 9.1 -> "CB: # 2_R19PSCellinfo"). Some have no number ("CB: # Rel20_AIoT").
- The template and example lines in sections 2.x and the "10.x" heading are skipped.
- The Drafts folders are named "CB # <n>_<Name>". Folder and notes do not always agree on the number: "CB # 17_R20_SON&MDT_Intra-CULTM" in Drafts vs "CB: # R20_SON&MDT_Intra-CULTM" in the notes. So the name part, ignoring case, spaces and punctuation, is the main match key, and the number only confirms it.

## Steps
1. **Reading comebacks** (new ingestion/ran3_comebacks.py): read only the visible text of the newest Chairs_Notes DOCX (same rule as the schedule, so deleted or struck-through text is ignored). Find pink "#" lines under numbered headings. Record number, name, agenda code, status (open if the line starts with "CB:", otherwise closed) and where in the file it came from.
   - A closed comeback is a pink "# n_Name" line without "CB:". It must still be pink, or tracked as a comeback in an earlier revision, so ordinary "#" text is never picked up.
   - If a comeback disappears from the notes entirely, keep its last-known agenda item from earlier revisions (cached in edit-history.json) and mark it **Removed**. Its Drafts folder still links.
2. **Matching folders**: for each Drafts folder starting with "CB", match it to a comeback by its name part, using a unique match only. Use the number to break ties. If more than one comeback could match, or none can, leave the folder unlinked and add a note to Verify data. Never guess.
3. **Publishing**: add a `comebacks` list (number, name, agenda code, status, folder) to the RAN3 schedule JSON, and record the agenda code on each tagged Drafts folder. This goes through the same build and checks.
4. **Schedule links**: a block that mentions "CB#n" or a comeback name takes that comeback's agenda code, before the existing topic matcher runs.
5. **App**:
   - My agenda (RAN3): list comebacks under each item, with their status badge.
   - Drafts: group the RAN3 folders by comeback, with Open ones first and Closed ones greyed.
   - Help: explain what "CB" means and how a comeback closes.
6. **Checks**:
   - Tests built from the real lines above: open, closed (no "CB:"), number missing, number mismatch (SON&MDT), template lines skipped, struck-through comeback ignored, two folders that could both match.
   - Health notes: list unlinked CB folders and comebacks that have no folder yet. A comeback without a folder is normal early in the week, so these are notes and never block publishing.
   - Rebuild RAN3#134 and check that each of the 18 CB folders links correctly in the preview.

## Technical notes
- Status comes only from text, never from colour alone. Pink identifies the line; "CB:" decides whether it is open. This stays correct if the chair later recolours closed lines.
- Matching key: lowercase name with "cb", "#", leading "<n>_" and non-alphanumerics removed. "Rel20"/"R20" are normalized.
- Folders that do not start with "CB" ("SONMDT offline", "RAN-CN Checkpoint") keep using the existing RAN3 topic matching.
- Record a rule in ingestion/AGENTS.md: "RAN3 comebacks link agenda items to Drafts folders by name; CB: prefix = open".
