import type { ScheduleBundle } from "@/types/schedule";

/**
 * Optional meeting-local schedule source.
 *
 * During a physical RAN1 meeting the 3GPP meeting network exposes a local file
 * server that usually carries fresher documents than the public site:
 *
 *   http://10.10.10.10/ftp/RAN/RAN1/Inbox/
 *
 * GitHub Actions can never reach that private address, so the public source
 * stays authoritative for the build pipeline. The probe below runs only in the
 * user's browser, is opt-in, fails fast, and never blocks the public schedule.
 *
 * The local server is expected to expose an ingestion-generated
 * `schedule.json` next to the DOCX inbox. If it only holds raw documents, the
 * probe reports the newest document version it can see so the UI can tell the
 * user that fresher material exists without silently parsing it client-side.
 */

export const DEFAULT_LOCAL_BASE = "http://10.10.10.10/ftp/RAN/RAN1/Inbox/";
const ENABLED_KEY = "ran1live.localSource.enabled";
const BASE_KEY = "ran1live.localSource.base";
const TIMEOUT_MS = 2500;

export type ScheduleOrigin = "public" | "meeting-local";

export interface LocalSourceSettings {
  enabled: boolean;
  baseUrl: string;
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

/**
 * Try the meeting-local server. Returns null whenever it is unreachable,
 * disabled, blocked by mixed content, or not newer than the public bundle.
 */
export async function probeLocalSchedule(
  publicBundle: ScheduleBundle | null,
): Promise<ScheduleBundle | null> {
  const { enabled, baseUrl } = getLocalSourceSettings();
  if (!enabled || typeof window === "undefined") return null;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const url = new URL("schedule.json", baseUrl).toString();
    const res = await fetch(url, { signal: controller.signal, cache: "no-store" });
    if (!res.ok) return null;
    const local = (await res.json()) as ScheduleBundle;
    if (!local?.sessions?.length) return null;

    const isNewer =
      !publicBundle || Date.parse(local.generatedAt) > Date.parse(publicBundle.generatedAt);
    if (!isNewer) return null;

    // Retain full provenance and label every source as meeting-local.
    return {
      ...local,
      sources: local.sources.map((s) => ({
        ...s,
        label: `${s.label} (meeting-local)`,
        url: s.url ?? new URL(s.fileName, baseUrl).toString(),
      })),
    };
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}
