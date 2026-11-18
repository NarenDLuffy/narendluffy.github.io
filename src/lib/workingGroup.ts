import { useSyncExternalStore } from "react";
import type { Meeting, WorkingGroup } from "@/types/meeting";

/**
 * The working group the user follows (RAN1 or RAN2). Every page reads the
 * meetings of the chosen group only; the choice is remembered per device.
 */
export const WORKING_GROUPS: WorkingGroup[] = ["RAN1", "RAN2"];

const KEY = "ran1live.workingGroup";
const listeners = new Set<() => void>();

export function groupOfMeeting(meeting: Pick<Meeting, "slug" | "workingGroup"> | undefined | null): WorkingGroup {
  if (meeting?.workingGroup) return meeting.workingGroup;
  return meeting?.slug?.toLowerCase().startsWith("ran2-") ? "RAN2" : "RAN1";
}

export function getWorkingGroup(): WorkingGroup {
  if (typeof window === "undefined") return "RAN1";
  try {
    return window.localStorage.getItem(KEY) === "RAN2" ? "RAN2" : "RAN1";
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

/** Live drafts trees for a group. RAN2 names the folder "Drafts". */
export function draftRoots(group: WorkingGroup) {
  const folder = group === "RAN2" ? "Drafts" : "drafts";
  const path = `/ftp/Meetings_3GPP_SYNC/${group}/Inbox/${folder}/`;
  return {
    venue: `http://10.10.10.10${path}`,
    venueHttps: `https://10.10.10.10${path}`,
    sync: `https://www.3gpp.org${path}`,
  };
}
