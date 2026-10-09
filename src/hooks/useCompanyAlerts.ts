import { useCallback, useEffect, useState } from "react";
import {
  cancelCompanyAlert,
  listCompanyAlerts,
  sendCompanyAlert,
  type CompanyAlert,
} from "@/lib/alerts.functions";
import { getIdentity } from "@/services/presenceService";

const DISMISS_KEY = "ran1live.company.dismissedAlerts.v1";
const CHANGED = "ran1live:alerts-changed";

function readDismissed(): string[] {
  try {
    return JSON.parse(window.localStorage.getItem(DISMISS_KEY) ?? "[]") as string[];
  } catch {
    return [];
  }
}

/** Company-wide "colleague needed" alerts, polled with presence cadence. */
export function useCompanyAlerts(meetingId: string | undefined) {
  const [alerts, setAlerts] = useState<CompanyAlert[]>([]);
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [now, setNow] = useState(() => Date.now());

  const refresh = useCallback(async () => {
    const id = getIdentity();
    if (!meetingId || !id.groupId) {
      setAlerts([]);
      return;
    }
    try {
      setAlerts(await listCompanyAlerts({ data: { groupCode: id.groupId, meetingId } }));
    } catch (e) {
      console.warn("alerts refresh failed", e);
    }
  }, [meetingId]);

  useEffect(() => {
    setDismissed(readDismissed());
    void refresh();
    const poll = setInterval(() => void refresh(), 15_000);
    const tick = setInterval(() => setNow(Date.now()), 30_000);
    const onVisible = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    const onChanged = () => void refresh();
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("focus", onVisible);
    window.addEventListener(CHANGED, onChanged);
    return () => {
      clearInterval(poll);
      clearInterval(tick);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("focus", onVisible);
      window.removeEventListener(CHANGED, onChanged);
    };
  }, [refresh]);

  const dismiss = useCallback((ids: string[]) => {
    const live = new Set(alerts.map((a) => a.id));
    const next = [...new Set([...readDismissed().filter((d) => live.has(d)), ...ids])];
    window.localStorage.setItem(DISMISS_KEY, JSON.stringify(next));
    setDismissed(next);
  }, [alerts]);

  const cancel = useCallback(async (alertId: string) => {
    const id = getIdentity();
    if (!id.groupId) return;
    await cancelCompanyAlert({ data: { groupCode: id.groupId, id: alertId, senderId: id.userId } });
    await refresh();
  }, [refresh]);

  const visible = alerts.filter(
    (a) => !dismissed.includes(a.id) && new Date(a.expiresAt).getTime() > now,
  );

  return { alerts: visible, dismiss, cancel, myUserId: getIdentityId() };
}

function getIdentityId() {
  return typeof window === "undefined" ? "" : getIdentity().userId;
}

/** Send an alert to everyone on this company code. */
export async function summonColleague(args: {
  meetingId: string;
  targetName: string;
  roomId: string;
  roomLabel?: string;
}) {
  const id = getIdentity();
  if (!id.groupId) throw new Error("Join your company group first.");
  await sendCompanyAlert({
    data: {
      groupCode: id.groupId,
      meetingId: args.meetingId,
      targetName: args.targetName,
      roomId: args.roomId,
      senderId: id.userId,
      ...(args.roomLabel ? { roomLabel: args.roomLabel } : {}),
      ...(id.displayName ? { senderName: id.displayName } : {}),
    },
  });
  window.dispatchEvent(new Event(CHANGED));
}
