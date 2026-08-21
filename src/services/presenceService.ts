import type { CoverageRow, CurrentPresence } from "@/types/presence";
import type { ScheduleBundle } from "@/types/schedule";
import { minutesOf } from "./scheduleService";

/**
 * Voluntary room presence for a company group.
 *
 * No accounts: a group is a shared code, a person is a display name stored on
 * the device. Presence is always scoped to a meeting id, expires by itself and
 * is never derived from location. This module is the only place that knows
 * where presence is stored, so the on-device store can be swapped for shared
 * realtime storage without touching any component.
 */

const GROUP_KEY = "ran1live.company.group";
const NAME_KEY = "ran1live.company.name";
const USER_KEY = "ran1live.company.userId";
const PRESENCE_KEY = "ran1live.company.presence.v1";
const FOLLOW_KEY = "ran1live.company.follows.v1";

export const PRESENCE_TTL_MINUTES = 120;

export interface PresenceStore {
  list(groupId: string, meetingId: string): Promise<CurrentPresence[]>;
  set(presence: CurrentPresence, groupId: string): Promise<void>;
  clear(userId: string, groupId: string, meetingId: string): Promise<void>;
}

type PresenceRecord = CurrentPresence & { groupId: string };

function readAll(): PresenceRecord[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(PRESENCE_KEY);
    const all = raw ? (JSON.parse(raw) as PresenceRecord[]) : [];
    const now = new Date().toISOString();
    return all.filter((p) => p.expiresAt > now);
  } catch {
    return [];
  }
}

function writeAll(records: PresenceRecord[]) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(PRESENCE_KEY, JSON.stringify(records));
  } catch {
    /* ignore */
  }
}

/** Default store: this device only. Fully private, useful offline. */
export const localPresenceStore: PresenceStore = {
  async list(groupId, meetingId) {
    return readAll().filter((p) => p.groupId === groupId && p.meetingId === meetingId);
  },
  async set(presence, groupId) {
    const others = readAll().filter(
      (p) =>
        !(
          p.userId === presence.userId &&
          p.groupId === groupId &&
          p.meetingId === presence.meetingId
        ),
    );
    writeAll([...others, { ...presence, groupId }]);
  },
  async clear(userId, groupId, meetingId) {
    writeAll(
      readAll().filter(
        (p) => !(p.userId === userId && p.groupId === groupId && p.meetingId === meetingId),
      ),
    );
  },
};

let store: PresenceStore = localPresenceStore;

export function setPresenceStore(next: PresenceStore) {
  store = next;
}

export function getPresenceStore(): PresenceStore {
  return store;
}

/* ---------- device identity (no accounts) ---------- */

export interface CompanyIdentity {
  userId: string;
  groupId: string;
  displayName: string;
}

function randomId() {
  return Math.random().toString(36).slice(2, 10);
}

export function getIdentity(): CompanyIdentity {
  if (typeof window === "undefined") return { userId: "", groupId: "", displayName: "" };
  let userId = window.localStorage.getItem(USER_KEY) ?? "";
  if (!userId) {
    userId = randomId();
    window.localStorage.setItem(USER_KEY, userId);
  }
  return {
    userId,
    groupId: window.localStorage.getItem(GROUP_KEY) ?? "",
    displayName: window.localStorage.getItem(NAME_KEY) ?? "",
  };
}

export function saveIdentity(next: { groupId?: string; displayName?: string }) {
  if (typeof window === "undefined") return;
  if (next.groupId !== undefined) {
    if (next.groupId) window.localStorage.setItem(GROUP_KEY, normalizeGroupCode(next.groupId));
    else window.localStorage.removeItem(GROUP_KEY);
  }
  if (next.displayName !== undefined) window.localStorage.setItem(NAME_KEY, next.displayName);
}

export function normalizeGroupCode(code: string): string {
  return code.trim().toLowerCase().replace(/\s+/g, "-");
}

/* ---------- presence operations ---------- */

export async function checkIn(args: {
  meetingId: string;
  roomId: string;
  sessionId?: string;
}): Promise<void> {
  const id = getIdentity();
  if (!id.groupId) return;
  const now = new Date();
  const presence: CurrentPresence = {
    userId: id.userId,
    organizationId: id.groupId,
    meetingId: args.meetingId,
    roomId: args.roomId,
    updatedAt: now.toISOString(),
    expiresAt: new Date(now.getTime() + PRESENCE_TTL_MINUTES * 60_000).toISOString(),
    ...(args.sessionId ? { sessionId: args.sessionId } : {}),
    ...(id.displayName ? { displayName: id.displayName } : {}),
  };
  await store.set(presence, id.groupId);
}

export async function checkOut(meetingId: string): Promise<void> {
  const id = getIdentity();
  if (!id.groupId) return;
  await store.clear(id.userId, id.groupId, meetingId);
}

export async function listPresence(meetingId: string): Promise<CurrentPresence[]> {
  const id = getIdentity();
  if (!id.groupId) return [];
  return store.list(id.groupId, meetingId);
}

/* ---------- follows (meeting-scoped agenda interest) ---------- */

type FollowMap = Record<string, string[]>;

export function getFollows(meetingId: string): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(FOLLOW_KEY);
    const map = raw ? (JSON.parse(raw) as FollowMap) : {};
    return map[meetingId] ?? [];
  } catch {
    return [];
  }
}

export function setFollows(meetingId: string, codes: string[]) {
  if (typeof window === "undefined") return;
  try {
    const raw = window.localStorage.getItem(FOLLOW_KEY);
    const map = raw ? (JSON.parse(raw) as FollowMap) : {};
    map[meetingId] = codes;
    window.localStorage.setItem(FOLLOW_KEY, JSON.stringify(map));
  } catch {
    /* ignore */
  }
}

/**
 * Coverage for the sessions running at `nowMinutes` on `date`, built entirely
 * from the current meeting's discovered rooms, sessions and agenda items.
 */
export function buildCoverage(
  bundle: ScheduleBundle,
  presence: CurrentPresence[],
  follows: string[],
  date: string,
  nowMinutes: number,
): CoverageRow[] {
  return bundle.sessions
    .filter((s) => s.date === date && s.kind !== "break" && s.kind !== "lunch")
    .filter((s) => minutesOf(s.startTime) <= nowMinutes && minutesOf(s.endTime) > nowMinutes)
    .map((s) => ({
      meetingId: bundle.meeting.id,
      sessionId: s.sessionId,
      topic: s.topic,
      agendaItems: s.agendaItems,
      roomId: s.roomId,
      roomName: s.roomName,
      startTime: s.startTime,
      endTime: s.endTime,
      colleaguesPresent: presence.filter((p) => p.roomId === s.roomId).length,
      colleaguesFollowing: s.agendaItems.filter((code) =>
        follows.some((f) => code === f || code.startsWith(`${f}.`)),
      ).length
        ? follows.filter((f) => s.agendaItems.some((c) => c === f || c.startsWith(`${f}.`))).length
        : 0,
    }));
}
