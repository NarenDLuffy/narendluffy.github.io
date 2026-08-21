/**
 * Which meeting the user is currently looking at.
 *
 * Empty means "whatever the meeting service considers current" — the default,
 * so a rollover to the next meeting needs no user action and no deployment.
 */

const KEY = "ran1live.selectedMeetingId";
const EVENT = "ran1live:meeting-selection";

const listeners = new Set<() => void>();

export function getSelectedMeetingId(): string {
  if (typeof window === "undefined") return "";
  try {
    return window.localStorage.getItem(KEY) ?? "";
  } catch {
    return "";
  }
}

export function setSelectedMeetingId(meetingId: string) {
  if (typeof window === "undefined") return;
  try {
    if (meetingId) window.localStorage.setItem(KEY, meetingId);
    else window.localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
  listeners.forEach((l) => l());
  window.dispatchEvent(new CustomEvent(EVENT));
}

export function subscribeSelection(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export const SELECTION_SERVER_SNAPSHOT = "";
