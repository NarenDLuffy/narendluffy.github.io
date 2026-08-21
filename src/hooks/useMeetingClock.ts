import { useEffect, useState } from "react";
import type { Meeting, Session } from "@/types/schedule";
import { minutesOf } from "@/services/schedule";

/** Ticking clock expressed in the meeting venue timezone. */
export function useMeetingClock(meeting: Meeting, tickMs = 30_000) {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    const tick = () => setNow(new Date());
    tick();
    const id = setInterval(tick, tickMs);
    return () => clearInterval(id);
  }, [tickMs]);

  const fmt = (opts: Intl.DateTimeFormatOptions) =>
    now
      ? new Intl.DateTimeFormat("en-GB", { timeZone: meeting.timezone, ...opts }).format(now)
      : "";

  const localTime = fmt({ hour: "2-digit", minute: "2-digit", hour12: false });
  const localDate = now
    ? new Intl.DateTimeFormat("en-CA", {
        timeZone: meeting.timezone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      }).format(now)
    : "";

  const nowMinutes = localTime ? minutesOf(localTime) : 0;

  return { ready: now !== null, now, localTime, localDate, nowMinutes };
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
