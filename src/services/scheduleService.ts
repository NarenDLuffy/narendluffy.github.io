import { queryOptions } from "@tanstack/react-query";
import { dataUrl } from "@/lib/dataUrl";
import type {
  AgendaItem,
  IngestStatus,
  Room,
  ScheduleBundle,
  ScheduleChange,
  ScheduleConflict,
  ScheduleSource,
  Session,
} from "@/types/schedule";
import type { Meeting } from "@/types/meeting";
import { probeLocalSchedule, type ScheduleOrigin } from "./localSource";

/**
 * Single read boundary for schedule data.
 *
 * The frontend never sees a DOCX: the ingestion pipeline publishes normalized
 * JSON per meeting under public/data/meetings/<slug>/. The last good bundle is
 * cached per meeting so a failed refresh never blanks the timetable.
 */

const cacheKey = (slug: string) => `ran1live.schedule.v2.${slug}`;

interface ScheduleFile {
  schemaVersion: number;
  generatedAt: string;
  meetingId: string;
  sessions: Session[];
  conflicts?: ScheduleConflict[];
  ingest?: IngestStatus;
}

export interface ScheduleResult {
  bundle: ScheduleBundle | null;
  /** true when served from local cache rather than a fresh download */
  stale: boolean;
  origin: ScheduleOrigin;
  error?: string;
}

function readCache(slug: string): ScheduleBundle | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(cacheKey(slug));
    return raw ? (JSON.parse(raw) as ScheduleBundle) : null;
  } catch {
    return null;
  }
}

function writeCache(slug: string, bundle: ScheduleBundle) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(cacheKey(slug), JSON.stringify(bundle));
  } catch {
    /* quota / private mode */
  }
}

async function getJson<T>(path: string, fallback: T): Promise<T> {
  const res = await fetch(dataUrl(path), { cache: "no-store" });
  if (res.status === 404) return fallback;
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${path}`);
  return (await res.json()) as T;
}

export async function loadSchedule(meeting: Meeting): Promise<ScheduleResult> {
  const slug = meeting.slug;
  if (typeof window === "undefined") {
    return { bundle: null, stale: false, origin: "public" };
  }

  let publicBundle: ScheduleBundle | null = null;
  let error: string | undefined;

  try {
    const dir = `meetings/${slug}`;
    const [schedule, rooms, agendaItems, sources, changes] = await Promise.all([
      getJson<ScheduleFile | null>(`${dir}/schedule.json`, null),
      getJson<Room[]>(`${dir}/rooms.json`, []),
      getJson<AgendaItem[]>(`${dir}/agenda.json`, []),
      getJson<ScheduleSource[]>(`${dir}/sources.json`, []),
      getJson<ScheduleChange[]>(`${dir}/changes.json`, []),
    ]);

    if (schedule) {
      publicBundle = {
        schemaVersion: schedule.schemaVersion ?? 1,
        generatedAt: schedule.generatedAt,
        meeting,
        rooms: [...rooms].sort((a, b) => a.order - b.order),
        sessions: schedule.sessions ?? [],
        agendaItems,
        sources,
        changes,
        conflicts: schedule.conflicts ?? [],
        ingest: schedule.ingest ?? {
          state: "ok",
          lastSuccessfulAt: schedule.generatedAt,
        },
      };
      writeCache(slug, publicBundle);
    }
  } catch (err) {
    error = (err as Error).message;
  }

  // Optional meeting-local source: used only when it is genuinely newer.
  const local = await probeLocalSchedule(meeting, publicBundle);
  if (local) {
    writeCache(slug, local);
    return { bundle: local, stale: false, origin: "meeting-local" };
  }

  if (publicBundle) return { bundle: publicBundle, stale: false, origin: "public" };

  const cached = readCache(slug);
  if (cached) return { bundle: { ...cached, meeting }, stale: true, origin: "public", error };

  // No schedule published yet for this meeting: that is a normal state before
  // meeting week, never an error page.
  return { bundle: null, stale: false, origin: "public", error };
}

export function scheduleQueryOptions(meeting: Meeting | undefined) {
  return queryOptions({
    queryKey: ["schedule", meeting?.id ?? "none"],
    queryFn: () => loadSchedule(meeting!),
    enabled: Boolean(meeting),
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
  });
}

/* ---------- derived helpers (pure, meeting-agnostic) ---------- */

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
