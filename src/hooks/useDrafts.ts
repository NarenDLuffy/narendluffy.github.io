import { useQuery } from "@tanstack/react-query";
import { useCallback, useMemo, useState, useSyncExternalStore } from "react";
import { buildActivity, draftsQueryOptions } from "@/services/draftService";
import {
  followedSince,
  getFollows,
  getPrefs,
  getSeenAt,
  markAllSeen,
  markSeen,
  setPrefs,
  subscribePrefs,
  toggleFollow,
} from "@/services/draftPreferences";
import { useBookmarks } from "./useBookmarks";
import type { Meeting } from "@/types/meeting";
import type { DraftNotificationPrefs } from "@/types/drafts";

/**
 * One hook for everything draft-related in the UI: the meeting's draft index,
 * the per-agenda rollup, and the device-local follow / seen / preference state.
 */
export function useDrafts(meeting?: Meeting) {
  const query = useQuery(draftsQueryOptions(meeting));
  const meetingId = meeting?.id ?? "";
  const { bookmarks } = useBookmarks();

  const version = useSyncExternalStore(
    subscribePrefs,
    () => (typeof window === "undefined" ? "" : window.localStorage.getItem("ran1live.draftSeen.v1") ?? ""),
    () => "",
  );
  const followVersion = useSyncExternalStore(
    subscribePrefs,
    () => (typeof window === "undefined" ? "" : window.localStorage.getItem("ran1live.draftFollows.v1") ?? ""),
    () => "",
  );
  const prefsVersion = useSyncExternalStore(
    subscribePrefs,
    () => (typeof window === "undefined" ? "" : window.localStorage.getItem("ran1live.draftPrefs.v1") ?? ""),
    () => "",
  );

  const index = query.data?.index ?? null;
  const follows = useMemo(() => (meetingId ? getFollows(meetingId) : []), [meetingId, followVersion]);
  const prefs = useMemo(() => getPrefs(), [prefsVersion]);

  const activity = useMemo(
    () =>
      buildActivity(index, {
        seenAt: (code) => (meetingId ? getSeenAt(meetingId, code) : undefined),
        since: (code) => (meetingId ? followedSince(meetingId, code) : undefined),
      }),
    [index, meetingId, version, followVersion],
  );

  /** Codes the user cares about, per their notification scope. */
  const watched = useMemo(() => {
    if (prefs.scope === "all") return [...activity.keys()];
    const set = new Set(prefs.scope === "followed" ? follows : [...follows, ...bookmarks]);
    return [...set];
  }, [prefs.scope, follows, bookmarks, activity]);

  /**
   * The user's own agenda: bookmarked items plus explicitly followed ones.
   * Independent of the notification scope, which only drives unread badges.
   */
  const myItems = useMemo(() => [...new Set([...follows, ...bookmarks])], [follows, bookmarks]);

  const unreadCount = useMemo(
    () => watched.reduce((sum, code) => sum + (activity.get(code)?.unreadCount ?? 0), 0),
    [watched, activity],
  );

  /**
   * Manual "Refresh now": rerun the live probe immediately (bypassing the 60s
   * cycle and staleTime) and report what reconciling the index changed.
   */
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<{
    at: string;
    added: number;
    updated: number;
    total: number;
    origin?: string | undefined;
    failed?: boolean | undefined;
  } | null>(null);

  const refreshNow = useCallback(async () => {
    setIsRefreshing(true);
    const before = new Map(
      (query.data?.index?.artifacts ?? []).map((a) => [a.id, a.modifiedAt ?? a.lastSeenAt ?? ""]),
    );
    try {
      const result = await query.refetch();
      const next = result.data?.index?.artifacts ?? [];
      let added = 0;
      let updated = 0;
      for (const a of next) {
        const prev = before.get(a.id);
        if (prev === undefined) added += 1;
        else if ((a.modifiedAt ?? a.lastSeenAt ?? "") !== prev) updated += 1;
      }
      setLastRefresh({
        at: new Date().toISOString(),
        added,
        updated,
        total: next.length,
        origin: result.data?.liveOrigin,
        failed: Boolean(result.error),
      });
    } catch {
      setLastRefresh({ at: new Date().toISOString(), added: 0, updated: 0, total: 0, failed: true });
    } finally {
      setIsRefreshing(false);
    }
  }, [query]);

  return {
    index,
    activity,
    follows,
    watched,
    unreadCount,
    prefs,
    stale: query.data?.stale ?? false,
    liveOrigin: query.data?.liveOrigin,
    liveCheckedAt: query.data?.liveCheckedAt,
    refresh: query.refetch,
    refreshNow,
    isRefreshing: isRefreshing || query.isFetching,
    lastRefresh,
    isLoading: query.isLoading,

    isFollowing: (code: string) => follows.includes(code),
    toggleFollow: useCallback(
      (code: string) => meetingId && toggleFollow(meetingId, code),
      [meetingId],
    ),
    markSeen: useCallback(
      (code: string) => meetingId && markSeen(meetingId, code),
      [meetingId],
    ),
    markAllSeen: useCallback(
      () => meetingId && markAllSeen(meetingId, [...activity.keys()]),
      [meetingId, activity],
    ),
    setPrefs: useCallback((next: Partial<DraftNotificationPrefs>) => setPrefs(next), []),
  };
}
