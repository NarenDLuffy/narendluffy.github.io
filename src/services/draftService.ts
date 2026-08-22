import { queryOptions } from "@tanstack/react-query";
import { dataUrl } from "@/lib/dataUrl";
import type { Meeting } from "@/types/meeting";
import type {
  AgendaActivity,
  DraftArtifact,
  DraftEvent,
  DraftFolder,
  DraftIndex,
} from "@/types/drafts";

/**
 * Read boundary for the draft / FL summary tracker.
 *
 * Deliberately separate from scheduleService: draft scanning runs on its own
 * cadence and must never delay or break the timetable. Both sides agree only
 * on agenda item codes.
 */

const cacheKey = (slug: string) => `ran1live.drafts.v1.${slug}`;

export const EVENT_LABEL: Record<DraftEvent["eventType"], string> = {
  NEW_FILE: "New file",
  FILE_UPDATED: "Updated",
  NEW_FOLDER: "New folder",
  NEW_ROUND: "New round",
  FL_SUMMARY_UPDATED: "FL summary",
  FILE_REMOVED: "Removed",
};

export interface DraftResult {
  index: DraftIndex | null;
  stale: boolean;
  error?: string;
}

function readCache(slug: string): DraftIndex | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(cacheKey(slug));
    return raw ? (JSON.parse(raw) as DraftIndex) : null;
  } catch {
    return null;
  }
}

export async function loadDrafts(meeting: Meeting): Promise<DraftResult> {
  const slug = meeting.slug;
  try {
    const res = await fetch(dataUrl(`meetings/${slug}/drafts.json`), { cache: "no-store" });
    if (res.status === 404) return { index: null, stale: false };
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const index = (await res.json()) as DraftIndex;
    if (typeof window !== "undefined") {
      try {
        window.localStorage.setItem(cacheKey(slug), JSON.stringify(index));
      } catch {
        /* quota */
      }
    }
    return { index, stale: false };
  } catch (err) {
    const cached = readCache(slug);
    return {
      index: cached,
      stale: Boolean(cached),
      error: err instanceof Error ? err.message : "draft index unavailable",
    };
  }
}

export function draftsQueryOptions(meeting?: Meeting) {
  return queryOptions({
    queryKey: ["drafts", meeting?.slug ?? "none"],
    queryFn: () => (meeting ? loadDrafts(meeting) : Promise.resolve({ index: null, stale: false })),
    enabled: Boolean(meeting),
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
  });
}

/* ---------- derivations ---------- */

export function foldersById(index: DraftIndex): Map<string, DraftFolder> {
  return new Map(index.folders.map((f) => [f.id, f]));
}

export function artifactsById(index: DraftIndex): Map<string, DraftArtifact> {
  return new Map(index.artifacts.map((a) => [a.id, a]));
}

export function artifactsForAgenda(index: DraftIndex, code: string): DraftArtifact[] {
  return index.artifacts
    .filter((a) => a.agendaItemId === code && !a.removedAt)
    .sort((a, b) => (b.modifiedAt ?? b.lastSeenAt).localeCompare(a.modifiedAt ?? a.lastSeenAt));
}

/**
 * Roll events up per agenda item. `seenAt` (per code) decides what is unread,
 * `since` suppresses history from before the user started following.
 */
export function buildActivity(
  index: DraftIndex | null,
  opts: {
    seenAt?: (code: string) => string | undefined;
    since?: (code: string) => string | undefined;
  } = {},
): Map<string, AgendaActivity> {
  const out = new Map<string, AgendaActivity>();
  if (!index) return out;

  const latestFl = new Map<string, DraftArtifact>();
  index.artifacts.forEach((a) => {
    if (a.fileType !== "fl_summary" || !a.agendaItemId || a.removedAt) return;
    const current = latestFl.get(a.agendaItemId);
    const stamp = a.modifiedAt ?? a.lastSeenAt;
    if (!current || stamp > (current.modifiedAt ?? current.lastSeenAt)) {
      latestFl.set(a.agendaItemId, a);
    }
  });

  index.events.forEach((e) => {
    const code = e.agendaItemId ?? "unmapped";
    const entry =
      out.get(code) ??
      ({
        agendaItemId: code,
        events: [],
        unread: [],
        unreadCount: 0,
        flUpdates: 0,
        newFiles: 0,
        newRounds: 0,
        latestFlSummary: latestFl.get(code),
      } as AgendaActivity);

    entry.events.push(e);
    if (e.eventType === "FL_SUMMARY_UPDATED") entry.flUpdates += 1;
    if (e.eventType === "NEW_FILE") entry.newFiles += 1;
    if (e.eventType === "NEW_ROUND") entry.newRounds += 1;

    const seen = opts.seenAt?.(code);
    const since = opts.since?.(code);
    const isUnread = (!seen || e.detectedAt > seen) && (!since || e.detectedAt >= since);
    if (isUnread) {
      entry.unread.push(e);
      entry.unreadCount = entry.unread.length;
    }
    if (!entry.latestAt || e.detectedAt > entry.latestAt) entry.latestAt = e.detectedAt;
    out.set(code, entry);
  });

  out.forEach((entry) => {
    entry.events.sort((a, b) => b.detectedAt.localeCompare(a.detectedAt));
    entry.unread.sort((a, b) => b.detectedAt.localeCompare(a.detectedAt));
  });
  return out;
}

export function formatSize(bytes?: number | null): string {
  if (!bytes || bytes <= 0) return "";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i += 1;
  }
  return `${value >= 10 || i === 0 ? Math.round(value) : value.toFixed(1)} ${units[i]}`;
}

export function relativeTime(iso?: string | null, now = Date.now()): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const mins = Math.round((now - then) / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}
