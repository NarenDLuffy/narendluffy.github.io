# Merge rooms that are the same room under a different name

## What's wrong today (RAN1#126bis)
The schedule shows 7 rooms instead of 5. Two extra columns come from rooms named in one chair file but not matched to a coloured room:
- "Yeongju A (1F)": 39 of its 44 slots have the same date, time and agenda as "Yeongju A Hall". Same room.
- "Yeongju B" (RAN1 Brk2): only 11 of 49 slots match "Yeongju B Hall" exactly. The rest are finer splits of the same blocks (for example 10.5.4.1 inside a 10.5.4 block), so it is very likely the same room too.

## Rule
A room that has only a name (no table colour) is folded into a coloured room when their schedules agree:
1. For each of its sessions, find a session in the coloured room on the same date whose time overlaps and whose agenda is the same or a parent/child (10.5.4 vs 10.5.4.1).
2. If most of its sessions agree (at least 70%) with one coloured room, and clearly more than with any other room, they are the same room.
3. The merged room keeps the coloured room's place and colour; the longer/more specific name wins as today, and a "RAN1 BrkN" label is kept.
4. A name similarity (e.g. "Yeongju A" inside "Yeongju A Hall") counts as supporting evidence, so a lower agreement (at least 50%) is enough when names also match. Names alone still never merge rooms.
5. Coloured rooms are never merged with each other (each colour is a separate room). Nothing about room names, chairs or the number of rooms is hard-coded.

After merging, the existing "most detailed version wins" logic picks the finer blocks for each slot.

## Result
RAN1#126bis shows 5 rooms. Same fix applies to every meeting (e.g. the extra "A3" room in 124 / 124bis is checked by the same rule and only merged if its schedule agrees).

## Technical details
- `ingestion/room_resolver.py`: after the colour/name pass, add a schedule-overlap pass for non-colour keepers; scoring by (date, time overlap, agenda prefix match); remap sessions, then rerun existing de-duplication.
- Add tests in `ingestion/tests/` for: matching-schedule merge, finer-split merge, unrelated room kept, ambiguous tie kept separate.
- Regenerate the 126bis data and check the room count; update the room-merging rule in AGENTS.md / project knowledge.
