import { useEffect, useState } from "react";
import { loadHealth, type HealthRecord } from "@/services/healthService";

/**
 * Latest health record for a meeting, refreshed when the tab regains focus.
 * The record is written by the background refresh jobs, so it changes without
 * this page doing anything.
 */
export function useMeetingHealth(slug: string | undefined): HealthRecord | null {
  const [health, setHealth] = useState<HealthRecord | null>(null);

  useEffect(() => {
    if (!slug) return;
    let alive = true;
    const load = () =>
      loadHealth(slug).then((record) => {
        if (alive) setHealth(record);
      });
    load();
    const onShow = () => {
      if (document.visibilityState === "visible") load();
    };
    document.addEventListener("visibilitychange", onShow);
    return () => {
      alive = false;
      document.removeEventListener("visibilitychange", onShow);
    };
  }, [slug]);

  return health;
}
