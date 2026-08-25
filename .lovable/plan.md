# Drafts: fix "My items" and drop the FL summaries tab

Agreed on both points. One clarification about the cause of what you're seeing.

## What's actually happening

"My items" currently reuses the *notification scope* setting rather than your agenda. Your device has that scope set to "Everything", so the tab lists every agenda item with activity. Your bookmarked agenda items (10.8.1, 10.8.2, 10.8.3) are not being used as the filter, and you have no followed items yet.

## Changes

1. **"My items" = My agenda + followed items, always.**
   The tab filters on bookmarked agenda items plus explicitly followed ones, independent of the notification-scope preference. Notification scope keeps only its real job: deciding what counts toward the unread badge.
2. **Remove the "FL summaries" tab.**
   Two tabs remain: "My items (n)" and "All agenda items". FL summaries are not lost — each agenda card keeps its FL count/updated badge, and FL files stay flagged in the file lists, so browsing "All agenda items" surfaces every folder's changes.
3. **Empty-state copy** for "My items" points to bookmarking agenda items or following them from a session.

## Technical notes

- `src/routes/drafts.index.tsx`: drop the `"fl"` filter value and its tab button; filter `watched` cards on a new `myItems` list instead of `drafts.watched`.
- `src/hooks/useDrafts.ts`: expose `myItems` = union of bookmarks and follows (scope-independent); leave `watched`/`unreadCount` as is for notifications.
- No changes to the scanner, data model, or ingestion.
