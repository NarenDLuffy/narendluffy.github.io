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
 * If the backend is unreachable (for example the fully static GitHub Pages
 * export, or offline at the venue), every call falls back to the device-only
 * store so the feature degrades instead of breaking.
 */

let remoteAvailable = true;

export const remotePresenceStore: PresenceStore = {
  async list(groupId, meetingId) {
    if (!remoteAvailable) return localPresenceStore.list(groupId, meetingId);
    try {
      const rows = await listRemotePresence({ data: { groupCode: groupId, meetingId } });
      return rows.map((r) => ({ ...r, organizationId: groupId })) as CurrentPresence[];
    } catch {
      remoteAvailable = false;
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
      remoteAvailable = true;
    } catch {
      remoteAvailable = false;
    }
  },

  async clear(userId, groupId, meetingId) {
    await localPresenceStore.clear(userId, groupId, meetingId);
    try {
      await clearRemotePresence({ data: { groupCode: groupId, userId, meetingId } });
      remoteAvailable = true;
    } catch {
      remoteAvailable = false;
    }
  },
};

export function isRemotePresenceAvailable() {
  return remoteAvailable;
}

/** Activate shared presence. Safe to call more than once. */
export function useSharedPresence() {
  setPresenceStore(remotePresenceStore);
}
