import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import type { CurrentPresence } from "@/types/presence";
import {
  checkIn,
  checkOut,
  getIdentity,
  listPresence,
  saveIdentity,
  type CompanyIdentity,
} from "@/services/presenceService";
import {
  getRemotePresenceStatus,
  subscribeRemotePresenceStatus,
  useSharedPresence,
} from "@/services/remotePresenceStore";

// Shared, backend-backed presence: check-ins are visible on every device that
// uses the same company code, not just the device that checked in.
useSharedPresence();

const serverStatus = { shared: true, lastError: null as string | null };
let cachedStatus = getRemotePresenceStatus();
function readStatus() {
  const s = getRemotePresenceStatus();
  if (s.shared !== cachedStatus.shared || s.lastError !== cachedStatus.lastError) cachedStatus = s;
  return cachedStatus;
}

/**
 * Account-free company presence for one meeting: a shared group code plus a
 * display name kept on the device. Everything is meeting-scoped, so switching
 * meetings never leaks presence between meeting weeks.
 */
export function useCompanyPresence(meetingId: string | undefined) {
  const [identity, setIdentity] = useState<CompanyIdentity>({
    userId: "",
    groupId: "",
    displayName: "",
  });
  const [presence, setPresence] = useState<CurrentPresence[]>([]);
  const status = useSyncExternalStore(subscribeRemotePresenceStatus, readStatus, () => serverStatus);

  useEffect(() => {
    setIdentity(getIdentity());
  }, []);

  const refresh = useCallback(async () => {
    if (!meetingId) return;
    setPresence(await listPresence(meetingId));
  }, [meetingId]);

  useEffect(() => {
    void refresh();
    const id = setInterval(() => void refresh(), 20_000);
    const onVisible = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("focus", onVisible);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("focus", onVisible);
    };
  }, [refresh, identity.groupId]);

  const join = useCallback((groupId: string, displayName: string) => {
    saveIdentity({ groupId, displayName });
    setIdentity(getIdentity());
  }, []);

  const leave = useCallback(async () => {
    if (meetingId) await checkOut(meetingId);
    saveIdentity({ groupId: "" });
    setIdentity(getIdentity());
    setPresence([]);
  }, [meetingId]);

  const enter = useCallback(
    async (roomId: string, sessionId?: string) => {
      if (!meetingId) return;
      await checkIn({ meetingId, roomId, ...(sessionId ? { sessionId } : {}) });
      await refresh();
    },
    [meetingId, refresh],
  );

  const exit = useCallback(async () => {
    if (!meetingId) return;
    await checkOut(meetingId);
    await refresh();
  }, [meetingId, refresh]);

  const mine = presence.find((p) => p.userId === identity.userId);

  return {
    identity,
    joined: Boolean(identity.groupId),
    presence,
    myRoomId: mine?.roomId ?? null,
    shared: status.shared,
    lastError: status.lastError,
    join,
    leave,
    enter,
    exit,
    refresh,
  };
}
