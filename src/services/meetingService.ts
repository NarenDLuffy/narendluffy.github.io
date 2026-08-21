import { queryOptions } from "@tanstack/react-query";
import { dataUrl } from "@/lib/dataUrl";
import type { Meeting, MeetingIndex, MeetingStatus } from "@/types/meeting";

/**
 * Meeting discovery, frontend side.
 *
 * The registry (public/data/meetings.json) is produced by the ingestion
 * pipeline. Nothing here knows about a specific RAN1 meeting: statuses are
 * recalculated from dates in the meeting timezone on every load so a meeting
 * becomes active / completed without any deployment.
 */

const CACHE_KEY = "ran1live.meetings.v1";

const EMPTY_INDEX: MeetingIndex = { schemaVersion: 1, generatedAt: "", meetings: [] };

/** Calendar day (YYYY-MM-DD) for `at` expressed in `timezone`. */
export function localDateIn(timezone: string, at: Date = new Date()): string {
  try {
    return new Intl.DateTimeFormat("en-CA", {
      timeZone: timezone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(at);
  } catch {
    return at.toISOString().slice(0, 10);
  }
}

/** Status is always derived from dates; an explicit override wins. */
export function computeStatus(meeting: Meeting, at: Date = new Date()): MeetingStatus {
  if (meeting.statusOverride) return meeting.statusOverride;
  const today = localDateIn(meeting.timezone || "UTC", at);
  if (today < meeting.startDate) return "upcoming";
  if (today > meeting.endDate) return "completed";
  return "active";
}

export function withComputedStatus(meetings: Meeting[], at: Date = new Date()): Meeting[] {
  return meetings
    .map((m) => ({ ...m, status: computeStatus(m, at) }))
    .sort((a, b) => b.startDate.localeCompare(a.startDate));
}

/**
 * Current-meeting priority: in progress -> nearest upcoming -> most recently
 * completed.
 */
export function selectCurrentMeeting(meetings: Meeting[]): Meeting | undefined {
  if (meetings.length === 0) return undefined;
  const active = meetings.filter((m) => m.status === "active");
  if (active.length > 0) {
    return [...active].sort((a, b) => a.startDate.localeCompare(b.startDate))[0];
  }
  const upcoming = meetings.filter((m) => m.status === "upcoming");
  if (upcoming.length > 0) {
    return [...upcoming].sort((a, b) => a.startDate.localeCompare(b.startDate))[0];
  }
  return [...meetings].sort((a, b) => b.endDate.localeCompare(a.endDate))[0];
}

export function daysUntil(meeting: Meeting, at: Date = new Date()): number {
  const today = new Date(`${localDateIn(meeting.timezone || "UTC", at)}T00:00:00Z`).getTime();
  const start = new Date(`${meeting.startDate}T00:00:00Z`).getTime();
  return Math.round((start - today) / 86_400_000);
}

export function formatDateRange(startDate: string, endDate: string): string {
  if (!startDate || !endDate) return "";
  const s = new Date(`${startDate}T00:00:00Z`);
  const e = new Date(`${endDate}T00:00:00Z`);
  const month = (d: Date) =>
    new Intl.DateTimeFormat("en-GB", { month: "short", timeZone: "UTC" }).format(d);
  const sameMonth = month(s) === month(e) && s.getUTCFullYear() === e.getUTCFullYear();
  return sameMonth
    ? `${s.getUTCDate()}–${e.getUTCDate()} ${month(e)} ${e.getUTCFullYear()}`
    : `${s.getUTCDate()} ${month(s)} – ${e.getUTCDate()} ${month(e)} ${e.getUTCFullYear()}`;
}

function readCache(): MeetingIndex | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(CACHE_KEY);
    return raw ? (JSON.parse(raw) as MeetingIndex) : null;
  } catch {
    return null;
  }
}

export async function loadMeetingIndex(): Promise<MeetingIndex> {
  if (typeof window === "undefined") return EMPTY_INDEX;
  try {
    const res = await fetch(dataUrl("meetings.json"), { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const index = (await res.json()) as MeetingIndex;
    if (!Array.isArray(index?.meetings)) throw new Error("malformed meeting registry");
    try {
      window.localStorage.setItem(CACHE_KEY, JSON.stringify(index));
    } catch {
      /* best effort */
    }
    return { ...index, meetings: withComputedStatus(index.meetings) };
  } catch {
    const cached = readCache();
    if (cached) return { ...cached, meetings: withComputedStatus(cached.meetings) };
    return EMPTY_INDEX;
  }
}

export const meetingIndexQueryOptions = queryOptions({
  queryKey: ["meetings"],
  queryFn: loadMeetingIndex,
  staleTime: 5 * 60_000,
  refetchInterval: 15 * 60_000,
});
