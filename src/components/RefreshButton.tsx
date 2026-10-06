import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import type { Meeting, ScheduleBundle } from "@/types/schedule";
import { cn } from "@/lib/utils";

function ago(iso: string | undefined, now: number): string {
  if (!iso) return "never";
  const minutes = Math.max(0, Math.round((now - Date.parse(iso)) / 60_000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  return hours < 48 ? `${hours} h ago` : `${Math.round(hours / 24)} days ago`;
}

/** Reloads the newest published schedule right away (no waiting for the 5-min poll). */
export function RefreshButton({ meeting, bundle }: { meeting: Meeting; bundle: ScheduleBundle | null }) {
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 30_000);
    return () => window.clearInterval(id);
  }, []);

  const refresh = async () => {
    setBusy(true);
    try {
      await Promise.all([
        queryClient.refetchQueries({ queryKey: ["schedule", meeting.id] }),
        queryClient.refetchQueries({ queryKey: ["meetings"] }),
      ]);
    } finally {
      setNow(Date.now());
      setBusy(false);
    }
  };

  return (
    <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
      <span>
        Schedule rebuilt {ago(bundle?.generatedAt, now)} · checks 3GPP for new versions every 5 min
      </span>
      <button
        type="button"
        onClick={refresh}
        disabled={busy}
        className="inline-flex min-h-9 shrink-0 items-center gap-1.5 rounded-md border border-border bg-card px-2.5 font-semibold text-foreground disabled:opacity-60"
      >
        <RefreshCw className={cn("size-3.5", busy && "animate-spin")} />
        Refresh
      </button>
    </div>
  );
}
