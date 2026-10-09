import type { CurrentPresence } from "@/types/presence";
import {
  localPresenceStore,
  setPresenceStore,
  type PresenceStore,
} from "./presenceService";
import {
  clearRemotePresence,
  listRemotePresence,
  setRemotePresence,
} from "@/lib/presence.functions";

/**
 * Shared presence store: check-ins go to the backend so every device using the
 * same company code sees the same room occupancy.
 *
 * On failure a call falls back to the device-only store, but the next call
 * always tries the backend again, and the status is exposed to the UI so a
 * silent "this device only" state can't happen.
 */

let remoteAvailable = true;
let lastError: string | null = null;
const listeners = new Set<() => void>();

function setStatus(ok: boolean, err?: unknown) {
  const nextErr = ok ? null : err instanceof Error ? err.message : String(err ?? "error");
  if (ok === remoteAvailable && nextErr === lastError) return;
  remoteAvailable = ok;
  lastError = nextErr;
  listeners.forEach((l) => l());
}

export const remotePresenceStore: PresenceStore = {
  async list(groupId, meetingId) {
    try {
      const rows = await listRemotePresence({ data: { groupCode: groupId, meetingId } });
      setStatus(true);
      return rows.map((r) => ({ ...r, organizationId: groupId })) as CurrentPresence[];
    } catch (e) {
      setStatus(false, e);
      return localPresenceStore.list(groupId, meetingId);
    }
  },

  async set(presence, groupId) {
    await localPresenceStore.set(presence, groupId);
    try {
      await setRemotePresence({
        data: {
          groupCode: groupId,
          userId: presence.userId,
          meetingId: presence.meetingId,
          roomId: presence.roomId,
          ...(presence.sessionId ? { sessionId: presence.sessionId } : {}),
          ...(presence.displayName ? { displayName: presence.displayName } : {}),
          expiresAt: presence.expiresAt,
        },
      });
      setStatus(true);
    } catch (e) {
      setStatus(false, e);
    }
  },

  async clear(userId, groupId, meetingId) {
    await localPresenceStore.clear(userId, groupId, meetingId);
    try {
      await clearRemotePresence({ data: { groupCode: groupId, userId, meetingId } });
      setStatus(true);
    } catch (e) {
      setStatus(false, e);
    }
  },
};

export function getRemotePresenceStatus() {
  return { shared: remoteAvailable, lastError };
}

export function subscribeRemotePresenceStatus(fn: () => void) {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

/** Activate shared presence. Safe to call more than once. */
export function useSharedPresence() {
  setPresenceStore(remotePresenceStore);
}
