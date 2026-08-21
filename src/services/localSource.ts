import type { ScheduleBundle } from "@/types/schedule";
import type { Meeting } from "@/types/meeting";

/**
 * Optional meeting-local schedule source.
 *
 * During a physical 3GPP meeting the venue network exposes a local file server
 * (conventionally http://10.10.10.10/) that often carries fresher documents
 * than the public site. Three hard rules:
 *
 *  1. GitHub Actions can never reach that private address, so the public path
 *     stays authoritative for the automated pipeline.
 *  2. Browsers may refuse the request entirely (mixed content, CORS, local
 *     network access restrictions). Access therefore goes through the
 *     LocalSourceTransport abstraction below so a helper app, extension,
 *     companion server or manual upload can replace the direct fetch later
 *     without touching any component.
 *  3. Being unreachable is the normal case and is never surfaced as an error.
 *
 * A local bundle is only adopted when it is genuinely newer: same meeting
 * identity, higher revision, different content hash, and it must parse into a
 * non-empty schedule. A newer timestamp alone is never sufficient.
 */

export const DEFAULT_LOCAL_BASE = "http://10.10.10.10/ftp/RAN/RAN1/Inbox/";
const ENABLED_KEY = "ran1live.localSource.enabled";
const BASE_KEY = "ran1live.localSource.base";
const TIMEOUT_MS = 2500;

export type ScheduleOrigin = "public" | "meeting-local";

export type LocalSourceState = "disabled" | "unavailable" | "available" | "newer";

export interface LocalSourceSettings {
  enabled: boolean;
  baseUrl: string;
}

export interface LocalSourceReport {
  state: LocalSourceState;
  /** Human summary, e.g. "Main schedule v08 · updated 14:41" */
  detail?: string;
  bundle?: ScheduleBundle;
}

/** Pluggable access layer for the meeting-local network. */
export interface LocalSourceTransport {
  readonly id: string;
  /** Resolve to a normalized bundle, or null when nothing usable is reachable. */
  fetchBundle(baseUrl: string, meeting: Meeting): Promise<ScheduleBundle | null>;
}

/**
 * Default transport: a direct browser fetch of an ingestion-generated
 * schedule.json sitting next to the DOCX inbox. Fails silently and fast.
 */
export const directFetchTransport: LocalSourceTransport = {
  id: "direct-fetch",
  async fetchBundle(baseUrl, meeting) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
    try {
      const url = `${baseUrl.replace(/\/$/, "")}/ran1live/${meeting.slug}/schedule-bundle.json`;
      const res = await fetch(url, { cache: "no-store", signal: controller.signal });
      if (!res.ok) return null;
      return (await res.json()) as ScheduleBundle;
    } catch {
      return null;
    } finally {
      clearTimeout(timer);
    }
  },
};

let transport: LocalSourceTransport = directFetchTransport;

/** Swap in a helper app / companion server / upload-based transport. */
export function setLocalSourceTransport(next: LocalSourceTransport) {
  transport = next;
}

export function getLocalSourceSettings(): LocalSourceSettings {
  if (typeof window === "undefined") return { enabled: false, baseUrl: DEFAULT_LOCAL_BASE };
  return {
    enabled: window.localStorage.getItem(ENABLED_KEY) === "1",
    baseUrl: window.localStorage.getItem(BASE_KEY) || DEFAULT_LOCAL_BASE,
  };
}

export function setLocalSourceSettings(next: Partial<LocalSourceSettings>) {
  if (typeof window === "undefined") return;
  if (next.enabled !== undefined) {
    window.localStorage.setItem(ENABLED_KEY, next.enabled ? "1" : "0");
  }
  if (next.baseUrl !== undefined) window.localStorage.setItem(BASE_KEY, next.baseUrl);
}

function revisionRank(parts: number[] | undefined): number {
  if (!parts || parts.length === 0) return -1;
  return parts.reduce((acc, p) => acc * 1000 + p, 0);
}

/** Highest revision rank across a bundle's sources. */
function topRevision(bundle: ScheduleBundle): number {
  return bundle.sources.reduce((max, s) => Math.max(max, revisionRank(s.revisionParts)), -1);
}

/**
 * Decides whether the local bundle supersedes the public one. Never decided on
 * a timestamp alone.
 */
export function localSupersedesPublic(
  local: ScheduleBundle,
  publicBundle: ScheduleBundle | null,
  meeting: Meeting,
): boolean {
  if (!local?.sessions?.length) return false;
  if (local.meeting?.id && local.meeting.id !== meeting.id) return false; // wrong meeting
  if (!publicBundle) return true;

  const localRev = topRevision(local);
  const publicRev = topRevision(publicBundle);
  if (localRev > publicRev) return true;
  if (localRev < publicRev) return false;

  // Equal revisions: only accept when content genuinely differs and the local
  // copy is not older.
  const localHashes = local.sources.map((s) => s.contentHash ?? "").join("|");
  const publicHashes = publicBundle.sources.map((s) => s.contentHash ?? "").join("|");
  if (localHashes === publicHashes) return false;
  return local.generatedAt > publicBundle.generatedAt;
}

export async function probeLocalSource(
  meeting: Meeting,
  publicBundle: ScheduleBundle | null,
): Promise<LocalSourceReport> {
  const { enabled, baseUrl } = getLocalSourceSettings();
  if (!enabled) return { state: "disabled" };

  const local = await transport.fetchBundle(baseUrl, meeting);
  if (!local) return { state: "unavailable" };

  const label = local.sources[0]?.label ?? "local schedule";
  const detail = `${label} · generated ${new Date(local.generatedAt).toLocaleTimeString()}`;

  if (localSupersedesPublic(local, publicBundle, meeting)) {
    return { state: "newer", detail, bundle: { ...local, meeting } };
  }
  return { state: "available", detail };
}

/** Convenience wrapper used by the schedule service. */
export async function probeLocalSchedule(
  meeting: Meeting,
  publicBundle: ScheduleBundle | null,
): Promise<ScheduleBundle | null> {
  const report = await probeLocalSource(meeting, publicBundle);
  return report.state === "newer" ? (report.bundle ?? null) : null;
}
