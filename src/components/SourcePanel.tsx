import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { RadioTower, Server } from "lucide-react";
import type { ScheduleBundle, SourceType } from "@/types/schedule";
import type { Meeting } from "@/types/meeting";
import {
  DEFAULT_LOCAL_BASE,
  getLocalSourceSettings,
  probeLocalSource,
  setLocalSourceSettings,
  type LocalSourceReport,
  type ScheduleOrigin,
} from "@/services/localSource";
import { cn } from "@/lib/utils";

const TYPE_LABEL: Record<SourceType, string> = {
  main_schedule: "Main schedule",
  chair_schedule: "Chair schedule",
  subchair_schedule: "Sub-chair schedule",
  online_schedule: "Online sessions",
  offline_schedule: "Offline sessions",
  room_schedule: "Room schedule",
  detailed_schedule: "Detailed schedule",
  venue_information: "Venue information",
  unknown_schedule: "Unclassified document",
};

export function SourcePanel({
  bundle,
  meeting,
  origin,
}: {
  bundle: ScheduleBundle;
  meeting: Meeting;
  origin: ScheduleOrigin;
}) {
  const qc = useQueryClient();
  const [enabled, setEnabled] = useState(false);
  const [baseUrl, setBaseUrl] = useState(DEFAULT_LOCAL_BASE);
  const [report, setReport] = useState<LocalSourceReport>({ state: "disabled" });

  useEffect(() => {
    const s = getLocalSourceSettings();
    setEnabled(s.enabled);
    setBaseUrl(s.baseUrl);
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (!enabled) {
      setReport({ state: "disabled" });
      return;
    }
    probeLocalSource(meeting, bundle).then((r) => {
      if (!cancelled) setReport(r);
    });
    return () => {
      cancelled = true;
    };
  }, [enabled, meeting, bundle]);

  const toggle = () => {
    const next = !enabled;
    setEnabled(next);
    setLocalSourceSettings({ enabled: next, baseUrl });
    qc.invalidateQueries({ queryKey: ["schedule"] });
  };

  const localLine = {
    disabled: "Meeting-local source off",
    unavailable: "Meeting-local source unavailable (normal outside the venue network)",
    available: `Meeting-local source available — not newer than the public documents`,
    newer: "Newer meeting-local revision in use",
  }[report.state];

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
        <span className="mono-code ml-auto text-[11px] text-muted-foreground">
          updated{" "}
          {new Intl.DateTimeFormat("en-GB", {
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
            timeZone: meeting.timezone,
          }).format(new Date(bundle.generatedAt))}
        </span>
      </div>

      <ul className="space-y-1">
        {bundle.sources.length === 0 ? (
          <li className="text-xs text-muted-foreground">No documents discovered yet.</li>
        ) : (
          bundle.sources.map((s) => (
            <li
              key={s.sourceId}
              className="mono-code text-[11px] leading-snug text-muted-foreground"
            >
              <span className="font-semibold text-foreground">{s.label}</span> ·{" "}
              {TYPE_LABEL[s.type]} · {s.fileName}
              {s.origin === "meeting-local" ? " · meeting-local" : ""}
            </li>
          ))
        )}
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
              Only reachable on the 3GPP meeting network, and only used when its documents are a
              genuinely newer revision. Automated builds always use the public source.
            </span>
          </span>
        </label>
        <p className="mono-code mt-2 text-[11px] text-muted-foreground">
          {localLine}
          {report.detail ? ` · ${report.detail}` : ""}
        </p>
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
