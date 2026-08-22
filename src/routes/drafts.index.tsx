import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { CheckCheck, Inbox, Settings2 } from "lucide-react";
import { useActiveMeeting } from "@/hooks/useActiveMeeting";
import { useDrafts } from "@/hooks/useDrafts";
import { MeetingBanner } from "@/components/MeetingBanner";
import { LoadingState, NoMeetingState } from "@/components/ScheduleStates";
import {
  AgendaActivityCard,
  ArtifactRow,
  EventRow,
  FollowButton,
} from "@/components/DraftActivity";
import { relativeTime, unmappedArtifacts } from "@/services/draftService";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/drafts/")({
  component: DraftsPage,
});

type Filter = "watched" | "all" | "fl";

function DraftsPage() {
  const { meeting, bundle, stale, isCurrent, isLoading } = useActiveMeeting();
  const drafts = useDrafts(meeting);
  const [filter, setFilter] = useState<Filter>("watched");
  const [showPrefs, setShowPrefs] = useState(false);

  const titleFor = useMemo(() => {
    const map = new Map((bundle?.agendaItems ?? []).map((a) => [a.code, a.title]));
    return (code: string) => map.get(code);
  }, [bundle]);

  if (isLoading) return <LoadingState label="Loading draft activity…" />;
  if (!meeting) return <NoMeetingState />;

  const index = drafts.index;
  const cards = [...drafts.activity.values()]
    .filter((a) => a.agendaItemId !== "unmapped")
    .filter((a) =>
      filter === "all"
        ? true
        : filter === "fl"
          ? a.flCount > 0 || a.flUpdates > 0
          : drafts.watched.includes(a.agendaItemId),
    )
    .sort((a, b) =>
      (b.latestAt ?? b.latestFileAt ?? "").localeCompare(a.latestAt ?? a.latestFileAt ?? ""),
    );

  // Files the scanner could not attach to an agenda item are never dropped.
  const unmapped = index ? unmappedArtifacts(index) : [];

  const feed = (index?.events ?? [])
    .slice()
    .sort((a, b) => b.detectedAt.localeCompare(a.detectedAt))
    .slice(0, 40);

  // Before any change is detected (fresh baseline) show the files themselves,
  // newest first, so the tracker is never an empty page.
  const recentFiles = (index?.artifacts ?? [])
    .filter((a) => !a.removedAt)
    .slice()
    .sort((a, b) =>
      (b.modifiedAt ?? b.lastSeenAt ?? "").localeCompare(a.modifiedAt ?? a.lastSeenAt ?? ""),
    )
    .slice(0, 40);

  return (
    <div className="space-y-5">
      <MeetingBanner meeting={meeting} bundle={bundle} stale={stale} isCurrent={isCurrent} />

      <header className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-lg font-semibold">Draft activity</h1>
          <p className="text-xs text-muted-foreground">
            Drafts and FL summaries uploaded under this meeting's Inbox, mapped to agenda items.
            {index?.lastSuccessfulScanAt
              ? ` Last checked ${relativeTime(index.lastSuccessfulScanAt)}.`
              : ""}
          </p>
        </div>
        <div className="flex shrink-0 gap-1.5">
          <button
            type="button"
            onClick={() => setShowPrefs((v) => !v)}
            aria-label="Notification settings"
            className="inline-flex min-h-9 items-center gap-1.5 rounded-md border border-border px-2.5 text-xs font-medium text-muted-foreground"
          >
            <Settings2 className="size-3.5" />
          </button>
          <button
            type="button"
            onClick={drafts.markAllSeen}
            className="inline-flex min-h-9 items-center gap-1.5 rounded-md border border-border px-2.5 text-xs font-medium text-muted-foreground"
          >
            <CheckCheck className="size-3.5" /> Mark all read
          </button>
        </div>
      </header>

      {showPrefs ? (
        <section className="space-y-3 rounded-lg border border-border bg-card p-3">
          <h2 className="text-sm font-semibold">Notify me about</h2>
          <div className="flex flex-wrap gap-1.5">
            {(
              [
                ["my-agenda", "My agenda + followed"],
                ["followed", "Only followed items"],
                ["all", "Everything"],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => drafts.setPrefs({ scope: value })}
                className={cn(
                  "min-h-9 rounded-md border px-2.5 text-xs font-medium",
                  drafts.prefs.scope === value
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border text-muted-foreground",
                )}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {(
              [
                ["flSummary", "FL summaries"],
                ["newFile", "New files"],
                ["fileUpdated", "Updated files"],
                ["newFolder", "New folders"],
                ["fileRemoved", "Removed files"],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => drafts.setPrefs({ [key]: !drafts.prefs[key] })}
                className={cn(
                  "min-h-9 rounded-md border px-2.5 text-xs font-medium",
                  drafts.prefs[key]
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border text-muted-foreground",
                )}
              >
                {label}
              </button>
            ))}
          </div>
          <p className="text-[11px] text-muted-foreground">
            Stored on this device — no account, nothing sent anywhere.
          </p>
        </section>
      ) : null}

      {!index ? (
        <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
          No draft folder has been published for {meeting.name} yet. This page fills in
          automatically once uploads start appearing under the meeting's Inbox.
        </p>
      ) : (
        <>
          <div className="flex gap-1.5">
            {(
              [
                ["watched", `My items (${drafts.unreadCount})`],
                ["fl", "FL summaries"],
                ["all", "All agenda items"],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => setFilter(value)}
                className={cn(
                  "min-h-9 flex-1 rounded-md border px-2.5 text-xs font-medium",
                  filter === value
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border text-muted-foreground",
                )}
              >
                {label}
              </button>
            ))}
          </div>

          {cards.length === 0 ? (
            <div className="space-y-2 rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
              <p className="flex items-center gap-2">
                <Inbox className="size-4" />
                {filter === "watched"
                  ? "Nothing yet for the agenda items you follow."
                  : index.scanState === "baseline"
                    ? "Baseline captured — you'll see uploads from here on."
                    : "No draft changes detected yet."}
              </p>
              {filter === "watched" ? (
                <p className="text-xs">
                  Follow agenda items below or on any session to get their draft updates here.
                </p>
              ) : null}
            </div>
          ) : (
            <ol className="space-y-1.5">
              {cards.map((a) => (
                <li key={a.agendaItemId} className="flex items-center gap-1.5">
                  <div className="min-w-0 flex-1">
                    <AgendaActivityCard activity={a} title={titleFor(a.agendaItemId)} />
                  </div>
                  <FollowButton
                    following={drafts.isFollowing(a.agendaItemId)}
                    onClick={() => drafts.toggleFollow(a.agendaItemId)}
                    label="Follow"
                  />
                </li>
              ))}
            </ol>
          )}

          {unmapped.length > 0 ? (
            <section>
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Unmapped draft activity
              </h2>
              <p className="mb-2 text-xs text-muted-foreground">
                {unmapped.length} file(s) discovered under the drafts tree that could not be
                matched to an agenda item. Nothing is discarded, and nothing is guessed.
              </p>
              <ol className="space-y-1.5">
                {unmapped.slice(0, 15).map((a) => (
                  <li key={a.id}>
                    <ArtifactRow artifact={a} />
                  </li>
                ))}
              </ol>
            </section>
          ) : null}

          <section>
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Everything, newest first
            </h2>
            {feed.length === 0 ? (
              <div className="space-y-1.5">
                <p className="text-xs text-muted-foreground">
                  {index.artifacts.length} file(s) indexed across {index.folders.length} folder(s).
                </p>
                <ol className="space-y-1.5">
                  {recentFiles.map((a) => (
                    <li key={a.id}>
                      <ArtifactRow artifact={a} />
                    </li>
                  ))}
                </ol>
              </div>
            ) : (
              <ol className="space-y-1.5">
                {feed.map((e) => (
                  <li key={e.id}>
                    <EventRow event={e} />
                  </li>
                ))}
              </ol>
            )}
          </section>
        </>
      )}
    </div>
  );
}
