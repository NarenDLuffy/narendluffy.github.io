import { useEffect, useState } from "react";
import type { Session } from "@/types/schedule";
import { minutesOf } from "@/services/scheduleService";

/**
 * Ticking clock expressed in the meeting timezone. NOW is always meeting-local,
 * never device-local; the device time is exposed separately so the UI can show
 * both when they differ.
 */
export function useMeetingClock(timezone: string, tickMs = 30_000) {
  const [now, setNow] = useState<Date | null>(null);
  const tz = timezone || "UTC";

  useEffect(() => {
    const tick = () => setNow(new Date());
    tick();
    const id = setInterval(tick, tickMs);
    return () => clearInterval(id);
  }, [tickMs]);

  const fmt = (opts: Intl.DateTimeFormatOptions, zone?: string) =>
    now
      ? new Intl.DateTimeFormat("en-GB", { timeZone: zone ?? tz, ...opts }).format(now)
      : "";

  const timeOpts: Intl.DateTimeFormatOptions = {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  };

  const localTime = fmt(timeOpts);
  const deviceZone =
    typeof Intl !== "undefined" ? Intl.DateTimeFormat().resolvedOptions().timeZone : tz;
  const deviceTime = fmt(timeOpts, deviceZone);

  const localDate = now
    ? new Intl.DateTimeFormat("en-CA", {
        timeZone: tz,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      }).format(now)
    : "";

  const nowMinutes = localTime ? minutesOf(localTime) : 0;

  return {
    ready: now !== null,
    now,
    timezone: tz,
    localTime,
    localDate,
    nowMinutes,
    deviceTime,
    deviceZone,
    differsFromDevice: Boolean(localTime && deviceTime && localTime !== deviceTime),
  };
}

export function isLive(session: Session, date: string, nowMinutes: number) {
  return (
    session.date === date &&
    minutesOf(session.startTime) <= nowMinutes &&
    minutesOf(session.endTime) > nowMinutes
  );
}

export function isUpcoming(session: Session, date: string, nowMinutes: number) {
  return session.date === date && minutesOf(session.startTime) > nowMinutes;
}
