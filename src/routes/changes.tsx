import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { scheduleQueryOptions, sessionMatchesAgenda } from "@/services/schedule";
import { useBookmarks } from "@/hooks/useBookmarks";
import { cn } from "@/lib/utils";
import type { ChangeType } from "@/types/schedule";

const LABEL: Record<ChangeType, string> = {
  room_changed: "Room changed",
  start_time_changed: "Start time changed",
  end_time_changed: "End time changed",
  session_added: "Session added",
  session_removed: "Session removed",
  agenda_item_added: "Agenda item added",
  agenda_item_removed: "Agenda item removed",
  agenda_item_moved: "Agenda item moved",
  session_renamed: "Session renamed",
  session_cancelled: "Session cancelled",
};

export const Route = createFileRoute("/changes")({
  head: () => ({
    meta: [
      { title: "Schedule changes — RAN1 Live" },
      {
        name: "description",
        content:
          "Every detected RAN1 schedule change: rooms moved, times shifted, sessions added or cancelled.",
      },
      { property: "og:title", content: "RAN1 schedule changes — RAN1 Live" },
      {
        property: "og:description",
        content: "Track what moved in the RAN1 schedule since the last document update.",
      },
    ],
  }),
  component: ChangesPage,
});

function ChangesPage() {
  const { data } = useQuery(scheduleQueryOptions);
  const { bookmarks } = useBookmarks();
  const [onlyMine, setOnlyMine] = useState(false);
  const bundle = data?.bundle;

  if (!bundle) return <p className="py-10 text-center text-sm text-muted-foreground">Loading…</p>;

  const changes = [...bundle.changes]
    .sort((a, b) => b.detectedAt.localeCompare(a.detectedAt))
    .filter((c) =>
      !onlyMine
        ? true
        : sessionMatchesAgenda(
            { agendaItems: c.agendaItems } as never,
            bookmarks,
          ) && bookmarks.length > 0,
    );

  const time = (iso: string) =>
    new Intl.DateTimeFormat("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: bundle.meeting.timezone,
    }).format(new Date(iso));

  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <h1 className="text-lg font-semibold">Schedule changes</h1>
        <p className="text-xs text-muted-foreground">
          Detected by comparing each parsed schedule with the previous verified version.
        </p>
      </header>

      <button
        type="button"
        onClick={() => setOnlyMine((v) => !v)}
        className={cn(
          "min-h-10 rounded-md border px-3 text-sm font-medium",
          onlyMine
            ? "border-primary bg-primary/10 text-primary"
            : "border-border bg-card text-muted-foreground",
        )}
      >
        Only changes affecting My agenda
      </button>

      <ol className="space-y-2">
        {changes.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
            No changes to show.
          </p>
        ) : (
          changes.map((c) => (
            <li key={c.changeId} className="rounded-lg border border-border bg-card p-3">
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-sm font-semibold">{c.title}</span>
                <span className="mono-code shrink-0 text-xs text-muted-foreground tabular">
                  {time(c.detectedAt)}
                </span>
              </div>
              <div className="mt-0.5 text-xs uppercase tracking-wide text-muted-foreground">
                {LABEL[c.type]}
              </div>
              <p className="mt-1 text-sm">{c.detail}</p>
              {c.from || c.to ? (
                <p className="mono-code mt-1 text-xs text-muted-foreground">
                  {c.from ? `${c.from} → ` : ""}
                  {c.to}
                </p>
              ) : null}
              <p className="mono-code mt-1 text-[11px] text-muted-foreground">
                Source: {c.sourceIds.join(", ")}
              </p>
            </li>
          ))
        )}
      </ol>

      {bundle.conflicts.filter((c) => !c.resolved).length > 0 ? (
        <section className="rounded-lg border border-warn/40 bg-warn/10 p-3">
          <h2 className="text-sm font-semibold">Unresolved source conflicts</h2>
          <p className="text-xs text-muted-foreground">
            Two documents disagree. These are never resolved automatically — an administrator
            decides.
          </p>
          <ul className="mt-2 space-y-1 text-xs">
            {bundle.conflicts
              .filter((c) => !c.resolved)
              .map((c) => (
                <li key={c.conflictId} className="mono-code">
                  {c.field}: {c.values.map((v) => `${v.sourceId}=${v.value}`).join("  vs  ")}
                </li>
              ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
