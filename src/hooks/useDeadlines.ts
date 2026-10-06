import { useCallback, useEffect, useState } from "react";

/**
 * FL summary deadlines the user enters per agenda item.
 *
 * The RAN1 email reflector is members-only, so deadlines cannot be read
 * automatically; they are kept on this device, per meeting.
 */
export interface Deadline {
  id: string;
  code: string;
  label: string;
  /** meeting-local date YYYY-MM-DD */
  date: string;
  /** meeting-local time HH:MM */
  time: string;
}

const key = (meetingId: string) => `ran1live.deadlines.v1.${meetingId}`;
const EVENT = "ran1live:deadlines";

function read(meetingId: string): Deadline[] {
  try {
    return JSON.parse(window.localStorage.getItem(key(meetingId)) ?? "[]") as Deadline[];
  } catch {
    return [];
  }
}

export function useDeadlines(meetingId: string | undefined) {
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);

  useEffect(() => {
    if (!meetingId) return;
    const sync = () => setDeadlines(read(meetingId));
    sync();
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, [meetingId]);

  const save = useCallback(
    (next: Deadline[]) => {
      if (!meetingId) return;
      window.localStorage.setItem(key(meetingId), JSON.stringify(next));
      window.dispatchEvent(new Event(EVENT));
    },
    [meetingId],
  );

  const add = useCallback(
    (d: Omit<Deadline, "id">) =>
      save([...(meetingId ? read(meetingId) : []), { ...d, id: crypto.randomUUID() }]),
    [meetingId, save],
  );
  const remove = useCallback(
    (id: string) => save((meetingId ? read(meetingId) : []).filter((d) => d.id !== id)),
    [meetingId, save],
  );

  return { deadlines, add, remove };
}
