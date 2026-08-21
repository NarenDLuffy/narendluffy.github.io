import { useCallback, useEffect, useState } from "react";

/**
 * Agenda-item bookmarks.
 *
 * Phase 1: anonymous, stored locally — no login required.
 * Phase 3: the same hook signature gets a Supabase-backed sync for
 * authenticated company delegates, so no component changes are needed.
 */

const KEY = "ran1live.bookmarks.v1";
const EVENT = "ran1live:bookmarks";

function read(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

export function useBookmarks() {
  const [items, setItems] = useState<string[]>([]);

  useEffect(() => {
    setItems(read());
    const sync = () => setItems(read());
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const persist = useCallback((next: string[]) => {
    const sorted = [...new Set(next)].sort();
    window.localStorage.setItem(KEY, JSON.stringify(sorted));
    setItems(sorted);
    window.dispatchEvent(new Event(EVENT));
  }, []);

  const toggle = useCallback(
    (code: string) => {
      const current = read();
      persist(
        current.includes(code) ? current.filter((c) => c !== code) : [...current, code],
      );
    },
    [persist],
  );

  const clear = useCallback(() => persist([]), [persist]);

  return {
    bookmarks: items,
    isBookmarked: (code: string) => items.includes(code),
    toggle,
    clear,
  };
}
