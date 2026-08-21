import { useCallback, useEffect, useState } from "react";
import type { CurrentPresence } from "@/types/presence";
import {
  checkIn,
  checkOut,
  getIdentity,
  listPresence,
  saveIdentity,
  type CompanyIdentity,
} from "@/services/presenceService";

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

  useEffect(() => {
    setIdentity(getIdentity());
  }, []);

  const refresh = useCallback(async () => {
    if (!meetingId) return;
    setPresence(await listPresence(meetingId));
  }, [meetingId]);

  useEffect(() => {
    void refresh();
    const id = setInterval(() => void refresh(), 60_000);
    return () => clearInterval(id);
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
    join,
    leave,
    enter,
    exit,
    refresh,
  };
}
