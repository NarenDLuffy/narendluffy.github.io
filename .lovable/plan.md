# Don't offer "call colleague" for people already in your room

## What's wrong
On the Company page, under "Colleagues by room", every named colleague gets a tappable "call" button as long as you're checked into a room — including colleagues who are already checked into that same room. So Test1, sitting in TamnaBC (5F) with you, can be "called to TamnaBC (5F)", which is meaningless.

The room page (`RoomColleagues`) already does this correctly: its call list only shows colleagues checked into *other* rooms. The Company page is the only place with the bug.

## Fix
In `src/routes/company.tsx`, in the "Colleagues by room" list:
- A colleague only gets the tappable "call" button when they are checked into a **different** room than yours (`p.roomId !== myRoomId`).
- Colleagues already in your room (and you) stay as plain name chips — no bell, no confirm dialog.
- The confirm dialog text and the alert banner itself need no change.

## Verify
- Two test users in the same room: neither shows a call button for the other on the Company page.
- Move one to another room: the call button appears, and tapping it still sends the alert as before.
- Room page behavior unchanged (already correct).
