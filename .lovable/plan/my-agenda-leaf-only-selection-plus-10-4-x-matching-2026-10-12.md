# My agenda: leaf-only selection plus 10.4.x matching

## Why

Agenda branches (e.g. 10.4 "Multiple carrier operation") are not where Tdocs live — only leaves are. Today you can star 10.4, but RAN1#126bis also has schedule blocks written as "10.4.x" (covering all children), which only match when you follow the branch itself. Following the leaves 10.4.1 and 10.4.2 misses those blocks.

Current data: 5 wildcard blocks exist — 10.4.x, 10.5.2.x, 10.5.4.x, 10.6.x, 10.8.x.

## 1. Only leaves can be selected

- On My agenda, the "Follow agenda items" chips list **leaf items only** — agenda items that have no children (no other agenda item names them as parent). 10.4, 10.5.4, etc. disappear; 10.4.1, 10.4.2, 10.5.4.1–4, 9.1, 9.2 stay.
- A branch with no children (a top-level item like 10.1 if it has no sub-items) stays selectable — it is a leaf itself.
- If the agenda unexpectedly yields no leaves, fall back to showing all items.
- Existing stars of a branch keep working (filtering logic unchanged for them); they just can't be newly selected from the chips.

## 2. "10.4.x" matches the selected leaves

- Extend the agenda match in `scheduleService.ts`: a session code ending in `.x` (e.g. `10.4.x`) matches any selected code that starts with the part before `.x` plus a dot — so `10.4.x` matches 10.4.1 and 10.4.2. This also covers 10.5.2.x, 10.5.4.x, 10.6.x, 10.8.x the same way, for any meeting.
- A `.x` block still matches the branch itself if someone follows it (existing stars keep working).
- One helper change covers every use: My agenda timeline, the Schedule "My agenda items" filter, and any session highlight.

## 3. Drafts filed at the branch level

- Draft folders often sit at the branch (e.g. `10.4 (...)`), so their artifacts carry the branch code. With leaf-only selection those drafts vanished from "Draft activity for my items" and from the chip badges.
- A draft filed at a branch code now counts for followers of any of its leaf children. In "Draft activity for my items" it appears once, not once per followed child; chip badges on each leaf include it.

## Verification

- My agenda chips for RAN1#126bis show leaves only: 10.4 and 10.5.4 gone, 10.4.1/10.4.2 and 10.5.4.1–4 present.
- Follow 10.4.1 + 10.4.2 → Schedule "My agenda items" highlights the 10.4.x blocks; My agenda timeline includes them.
- The 10.5.4.x and 10.8.x blocks light up when their leaves are followed.
- Draft activity for a leaf includes drafts filed under its branch folder, shown once.
- Check phone and desktop widths; confirm no build or preview errors.

## Technical details

- `src/services/scheduleService.ts`: extend `agendaMatches` with the `.x` wildcard rule (pure helper, no data change).
- `src/routes/agenda.tsx`: compute leaves from `bundle.agendaItems` (an item is a leaf when no other item has it as `parent`); render only leaves.
- `src/services/draftService.ts` (activity roll-up for My agenda) and the badge counts in `src/routes/agenda.tsx`: include drafts whose agenda code is an ancestor of the followed leaf; dedupe the list.
- No ingestion change and no data rebuild needed — the schedule JSON already contains the `.x` codes as written in the source documents.
