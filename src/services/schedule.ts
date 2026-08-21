import { queryOptions } from "@tanstack/react-query";
import { mockSchedule } from "@/data/mockSchedule";
import type { ScheduleBundle, Session } from "@/types/schedule";

/**
 * Single read boundary for schedule data.
 *
 * Phase 1: bundled mock data, with an opportunistic fetch of the statically
 * generated /schedule/schedule.json (produced by the Python ingestion pipeline
 * and deployed with the site). Phase 2 flips the primary source to the fetched
 * file; the last good bundle is cached so a failed refresh never blanks the UI.
 */

const CACHE_KEY = "ran1live.schedule.cache.v1";

function readCache(): ScheduleBundle | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(CACHE_KEY);
    return raw ? (JSON.parse(raw) as ScheduleBundle) : null;
  } catch {
    return null;
  }
}

function writeCache(bundle: ScheduleBundle) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(CACHE_KEY, JSON.stringify(bundle));
  } catch {
    /* quota / private mode: cache is best-effort */
  }
}

export interface ScheduleResult {
  bundle: ScheduleBundle;
  /** true when served from local cache or bundled fallback */
  stale: boolean;
  error?: string;
}

export async function loadSchedule(): Promise<ScheduleResult> {
  if (typeof window === "undefined") {
    return { bundle: mockSchedule, stale: false };
  }
  try {
    const res = await fetch("/schedule/schedule.json", { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const bundle = (await res.json()) as ScheduleBundle;
    if (!bundle?.sessions?.length) throw new Error("empty schedule");
    writeCache(bundle);
    return { bundle, stale: false };
  } catch (err) {
    const cached = readCache();
    if (cached) {
      return { bundle: cached, stale: true, error: (err as Error).message };
    }
    // Reliability rule: never render an empty timetable.
    return { bundle: mockSchedule, stale: true, error: (err as Error).message };
  }
}

export const scheduleQueryOptions = queryOptions({
  queryKey: ["schedule"],
  queryFn: loadSchedule,
  staleTime: 60_000,
  refetchInterval: 5 * 60_000,
});

/* ---------- derived helpers (pure) ---------- */

export function minutesOf(hhmm: string): number {
  const [h = 0, m = 0] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

export function sessionsForDate(bundle: ScheduleBundle, date: string): Session[] {
  return bundle.sessions.filter((s) => s.date === date);
}

export function meetingDates(bundle: ScheduleBundle): { date: string; day: string }[] {
  const seen = new Map<string, string>();
  bundle.sessions.forEach((s) => seen.set(s.date, s.day));
  return [...seen.entries()]
    .map(([date, day]) => ({ date, day }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

export function sourceLabel(bundle: ScheduleBundle, sourceId: string): string {
  return bundle.sources.find((s) => s.sourceId === sourceId)?.label ?? sourceId;
}

/** Matches an agenda code against a filter, including child items of a parent. */
export function agendaMatches(code: string, filter: string): boolean {
  return code === filter || code.startsWith(`${filter}.`);
}

export function sessionMatchesAgenda(session: Session, filters: string[]): boolean {
  if (filters.length === 0) return true;
  return session.agendaItems.some((code) => filters.some((f) => agendaMatches(code, f)));
}

export function searchSession(session: Session, q: string): boolean {
  if (!q.trim()) return true;
  const needle = q.trim().toLowerCase();
  return [
    session.topic,
    session.roomName,
    session.sessionLead ?? "",
    session.day,
    ...session.agendaItems,
  ]
    .join(" ")
    .toLowerCase()
    .includes(needle);
}
