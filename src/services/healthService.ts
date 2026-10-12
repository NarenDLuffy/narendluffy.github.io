/**
 * The per-meeting health record the refresh jobs write (see ingestion/health.py).
 *
 * It is generated data, so it is read the same way the schedule and drafts are:
 * the live repo copy first, the bundled copy as fallback.
 */
import { fetchData } from "@/lib/dataUrl";

export type HealthWarning = { level: "warn" | "info"; text: string };

export type HealthSection = {
  state?: string;
  lastSuccessAt?: string;
  lastAttemptAt?: string;
  source?: string;
  sessionCount?: number;
  roomCount?: number;
  artifactCount?: number;
  hiddenCount?: number;
  folderCount?: number;
  readFolderCount?: number;
  conflictCount?: number;
  lowConfidenceCount?: number;
  draftOnly?: boolean;
  dates?: string[];
  sources?: { label?: string; fileName?: string; origin?: string }[];
};

export type HealthRecord = {
  schemaVersion: number;
  meetingId: string;
  updatedAt?: string;
  schedule?: HealthSection;
  drafts?: HealthSection;
  remoteFtp?: { state?: string; host?: string | null; credentials?: boolean };
  detectedHost?: string;
  warnings?: HealthWarning[];
};

export async function loadHealth(slug: string): Promise<HealthRecord | null> {
  try {
    const res = await fetchData(`meetings/${slug}/health.json`);
    if (!res.ok) return null;
    return (await res.json()) as HealthRecord;
  } catch {
    return null;
  }
}
