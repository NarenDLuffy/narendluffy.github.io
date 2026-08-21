import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { RadioTower, Server } from "lucide-react";
import type { ScheduleBundle } from "@/types/schedule";
import {
  DEFAULT_LOCAL_BASE,
  getLocalSourceSettings,
  setLocalSourceSettings,
} from "@/services/localSource";
import type { ScheduleOrigin } from "@/services/localSource";
import { cn } from "@/lib/utils";

export function SourcePanel({
  bundle,
  origin,
}: {
  bundle: ScheduleBundle;
  origin: ScheduleOrigin;
}) {
  const qc = useQueryClient();
  const [enabled, setEnabled] = useState(false);
  const [baseUrl, setBaseUrl] = useState(DEFAULT_LOCAL_BASE);

  useEffect(() => {
    const s = getLocalSourceSettings();
    setEnabled(s.enabled);
    setBaseUrl(s.baseUrl);
  }, []);

  const toggle = () => {
    const next = !enabled;
    setEnabled(next);
    setLocalSourceSettings({ enabled: next, baseUrl });
    qc.invalidateQueries({ queryKey: ["schedule"] });
  };

  return (
    <section className="space-y-2 rounded-lg border border-border bg-card p-3">
      <div className="flex items-center gap-2">
        {origin === "meeting-local" ? (
          <RadioTower className="size-4 text-live" />
        ) : (
          <Server className="size-4 text-muted-foreground" />
        )}
        <h2 className="text-sm font-semibold">
          {origin === "meeting-local" ? "Meeting-local source" : "Public 3GPP source"}
        </h2>
      </div>

      <ul className="space-y-1">
        {bundle.sources.map((s) => (
          <li key={s.sourceId} className="mono-code text-[11px] leading-snug text-muted-foreground">
            <span className="font-semibold text-foreground">{s.label}</span> · {s.role} ·{" "}
            {s.fileName}
          </li>
        ))}
      </ul>

      <div className="rounded-md border border-dashed border-border p-2.5">
        <label className="flex items-start gap-2 text-xs">
          <input
            type="checkbox"
            checked={enabled}
            onChange={toggle}
            className="mt-0.5 size-4 accent-[var(--primary)]"
          />
          <span>
            <span className="block font-medium text-foreground">
              Use meeting-local server when available
            </span>
            <span className="block text-muted-foreground">
              Only works on the 3GPP meeting network. Used only when its documents are newer than
              the public ones; automated builds always use the public source.
            </span>
          </span>
        </label>
        <input
          value={baseUrl}
          onChange={(e) => {
            setBaseUrl(e.target.value);
            setLocalSourceSettings({ baseUrl: e.target.value });
          }}
          className={cn(
            "mono-code mt-2 min-h-10 w-full rounded-md border border-input bg-background px-2 text-[11px] outline-none focus:ring-2 focus:ring-ring",
            !enabled && "opacity-50",
          )}
          disabled={!enabled}
          spellCheck={false}
        />
      </div>
    </section>
  );
}
