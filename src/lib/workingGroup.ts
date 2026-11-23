import { useSyncExternalStore } from "react";
import type { Meeting, WorkingGroup } from "@/types/meeting";

/**
 * The working group the user follows (RAN Plenary, RAN1–RAN4, SA2). Every page reads the
 * meetings of the chosen group only; the choice is remembered per device.
 */
export const WORKING_GROUPS: WorkingGroup[] = ["RAN", "RAN1", "RAN2", "RAN3", "RAN4", "SA2"];

/** Display name: the plenary reads better spelled out. */
export function groupLabel(group: WorkingGroup): string {
  return group === "RAN" ? "RAN Plenary" : group;
}

const KEY = "ran1live.workingGroup";
const listeners = new Set<() => void>();

export function groupOfMeeting(meeting: Pick<Meeting, "slug" | "workingGroup"> | undefined | null): WorkingGroup {
  if (meeting?.workingGroup) return meeting.workingGroup;
  const slug = meeting?.slug?.toLowerCase() ?? "";
  if (slug.startsWith("ran2-")) return "RAN2";
  if (slug.startsWith("ran3-")) return "RAN3";
  if (slug.startsWith("ran4-")) return "RAN4";
  if (slug.startsWith("sa2-")) return "SA2";
  if (slug.startsWith("ran-")) return "RAN";
  return "RAN1";
}

export function getWorkingGroup(): WorkingGroup {
  if (typeof window === "undefined") return "RAN1";
  try {
    const v = window.localStorage.getItem(KEY);
    return v === "RAN" || v === "RAN2" || v === "RAN3" || v === "RAN4" || v === "SA2" ? v : "RAN1";
  } catch {
    return "RAN1";
  }
}

export function setWorkingGroup(group: WorkingGroup) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(KEY, group);
  } catch {
    /* ignore */
  }
  listeners.forEach((l) => l());
}

export function subscribeWorkingGroup(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useWorkingGroup(): WorkingGroup {
  return useSyncExternalStore(subscribeWorkingGroup, getWorkingGroup, () => "RAN1" as WorkingGroup);
}

/** Live drafts trees for a group. RAN2 and RAN3 name the folder "Drafts". */
export function draftRoots(group: WorkingGroup) {
  const folder = group !== "RAN1" ? "Drafts" : "drafts";
  const path = `/ftp/Meetings_3GPP_SYNC/${group}/Inbox/${folder}/`;
  return {
    venue: `http://10.10.10.10${path}`,
    venueHttps: `https://10.10.10.10${path}`,
    sync: `https://www.3gpp.org${path}`,
  };
}
