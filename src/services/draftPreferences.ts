/**
 * Personal draft-tracking state: follows, "since I last looked" markers and
 * notification preferences.
 *
 * RAN1 Live has no accounts, so this lives on the device. All of it is keyed
 * by meeting so a rollover to the next RAN1 meeting starts clean while old
 * meetings keep their state.
 */

const FOLLOW_KEY = "ran1live.draftFollows.v1";
const SEEN_KEY = "ran1live.draftSeen.v1";
const PREFS_KEY = "ran1live.draftPrefs.v1";
export const DRAFT_PREFS_EVENT = "ran1live:draftprefs";

import type { DraftNotificationPrefs } from "@/types/drafts";

export const DEFAULT_PREFS: DraftNotificationPrefs = {
  scope: "my-agenda",
  newFile: true,
  fileUpdated: true,
  flSummary: true,
  newRound: true,
  fileRemoved: false,
  grouping: "grouped",
};

type FollowMap = Record<string, { codes: string[]; since: Record<string, string> }>;
type SeenMap = Record<string, Record<string, string>>;

function read<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, value: unknown) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* private mode */
  }
  window.dispatchEvent(new Event(DRAFT_PREFS_EVENT));
}

export function subscribePrefs(cb: () => void) {
  if (typeof window === "undefined") return () => undefined;
  window.addEventListener(DRAFT_PREFS_EVENT, cb);
  window.addEventListener("storage", cb);
  return () => {
    window.removeEventListener(DRAFT_PREFS_EVENT, cb);
    window.removeEventListener("storage", cb);
  };
}

/* ---------- follows ---------- */

export function getFollows(meetingId: string): string[] {
  return read<FollowMap>(FOLLOW_KEY, {})[meetingId]?.codes ?? [];
}

/**
 * Following starts "from now": existing files stay browsable but never arrive
 * as a burst of notifications.
 */
export function toggleFollow(meetingId: string, code: string): void {
  const map = read<FollowMap>(FOLLOW_KEY, {});
  const entry = map[meetingId] ?? { codes: [], since: {} };
  if (entry.codes.includes(code)) {
    entry.codes = entry.codes.filter((c) => c !== code);
    delete entry.since[code];
  } else {
    entry.codes = [...entry.codes, code].sort();
    entry.since[code] = new Date().toISOString();
  }
  map[meetingId] = entry;
  write(FOLLOW_KEY, map);
}

export function followedSince(meetingId: string, code: string): string | undefined {
  return read<FollowMap>(FOLLOW_KEY, {})[meetingId]?.since[code];
}

/* ---------- since I last looked ---------- */

export function getSeenAt(meetingId: string, code: string): string | undefined {
  return read<SeenMap>(SEEN_KEY, {})[meetingId]?.[code];
}

export function markSeen(meetingId: string, code: string, at = new Date().toISOString()) {
  const map = read<SeenMap>(SEEN_KEY, {});
  map[meetingId] = { ...(map[meetingId] ?? {}), [code]: at };
  write(SEEN_KEY, map);
}

export function markAllSeen(meetingId: string, codes: string[]) {
  const at = new Date().toISOString();
  const map = read<SeenMap>(SEEN_KEY, {});
  const entry = { ...(map[meetingId] ?? {}) };
  codes.forEach((c) => {
    entry[c] = at;
  });
  map[meetingId] = entry;
  write(SEEN_KEY, map);
}

/* ---------- notification preferences ---------- */

export function getPrefs(): DraftNotificationPrefs {
  return { ...DEFAULT_PREFS, ...read<Partial<DraftNotificationPrefs>>(PREFS_KEY, {}) };
}

export function setPrefs(next: Partial<DraftNotificationPrefs>) {
  write(PREFS_KEY, { ...getPrefs(), ...next });
}
