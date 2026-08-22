import { Link } from "@tanstack/react-router";
import { Bell, BellRing, FileText, FolderOpen, Sparkles } from "lucide-react";
import { eventLabel, formatSize, relativeTime } from "@/services/draftService";
import { cn } from "@/lib/utils";
import type { AgendaActivity, DraftArtifact, DraftEvent } from "@/types/drafts";

const TONE: Record<DraftEvent["eventType"], string> = {
  NEW_FILE: "bg-secondary text-foreground border-border",
  FILE_UPDATED: "bg-secondary text-muted-foreground border-border",
  NEW_FOLDER: "bg-secondary text-muted-foreground border-border",
  FILE_REMOVED: "bg-destructive/10 text-destructive border-destructive/30",
  FOLDER_REMOVED: "bg-destructive/10 text-destructive border-destructive/30",
};

// Semantics, when the scanner is confident, get their own emphasis.
const SEMANTIC_TONE: Record<string, string> = {
  FL_SUMMARY_UPDATED: "bg-primary/10 text-primary border-primary/30",
  NEW_ROUND: "bg-live/10 text-live border-live/30",
  NEW_FL_FOLDER: "bg-primary/10 text-primary border-primary/30",
};

export function EventBadge({ event }: { event: DraftEvent }) {
  const tone =
    (event.semanticType ? SEMANTIC_TONE[event.semanticType] : undefined) ??
    TONE[event.eventType];
  return (
    <span
      className={cn(
        "mono-code shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase",
        tone,
      )}
    >
      {eventLabel(event)}
    </span>
  );
}

/** Small unread pill used on session cards and agenda chips. */
export function DraftBadge({ count, important }: { count: number; important?: boolean }) {
  if (count <= 0) return null;
  return (
    <span
      className={cn(
        "inline-flex min-w-5 items-center justify-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-bold",
        important ? "bg-primary text-primary-foreground" : "bg-secondary text-foreground",
      )}
      title={`${count} draft update${count === 1 ? "" : "s"} since you last looked`}
    >
      {important ? <Sparkles className="size-2.5" /> : null}
      {count}
    </span>
  );
}

export function FollowButton({
  following,
  onClick,
  label = "Follow drafts",
}: {
  following: boolean;
  onClick: () => void;
  label?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex min-h-9 items-center gap-1.5 rounded-md border px-2.5 text-xs font-medium",
        following
          ? "border-primary bg-primary/10 text-primary"
          : "border-border bg-card text-muted-foreground",
      )}
    >
      {following ? <BellRing className="size-3.5" /> : <Bell className="size-3.5" />}
      {following ? "Following" : label}
    </button>
  );
}

export function EventRow({ event }: { event: DraftEvent }) {
  const body = (
    <>
      <EventBadge event={event} />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium">{event.title}</span>
        <span className="block truncate text-xs text-muted-foreground">
          {event.agendaItemId ? (
            <span className="mono-code mr-1.5">{event.agendaItemId}</span>
          ) : null}
          {event.detail ?? event.folderPath}
        </span>
      </span>
      <span className="mono-code shrink-0 text-[11px] text-muted-foreground">
        {relativeTime(event.detectedAt)}
      </span>
    </>
  );

  const className =
    "flex items-center gap-2 rounded-md border border-border bg-card p-2.5 hover:bg-secondary/60";

  return event.url ? (
    <a href={event.url} target="_blank" rel="noreferrer" className={className}>
      {body}
    </a>
  ) : (
    <div className={className}>{body}</div>
  );
}

export function ArtifactRow({ artifact }: { artifact: DraftArtifact }) {
  const isFl = artifact.fileType === "fl_summary";
  const rev = artifact.revisions?.length ?? 0;
  const body = (
    <>
      <FileText className={cn("size-4 shrink-0", isFl ? "text-primary" : "text-muted-foreground")} />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium">{artifact.filename}</span>
        <span className="block truncate text-xs text-muted-foreground">
          {isFl ? "FL summary · " : ""}
          {formatSize(artifact.size)}
          {rev > 1 ? ` · ${rev} revisions` : ""}
          {artifact.sources.length > 1 ? " · local + public" : ""}
        </span>
      </span>
      <span className="mono-code shrink-0 text-[11px] text-muted-foreground">
        {relativeTime(artifact.modifiedAt ?? artifact.lastSeenAt)}
      </span>
    </>
  );
  const className =
    "flex items-center gap-2 rounded-md border border-border bg-card p-2.5 hover:bg-secondary/60";
  return artifact.sources[0]?.url ? (
    <a href={artifact.sources[0].url} target="_blank" rel="noreferrer" className={className}>
      {body}
    </a>
  ) : (
    <div className={className}>{body}</div>
  );
}

/** Compact per-agenda-item summary card used on NOW and My agenda. */
export function AgendaActivityCard({
  activity,
  title,
}: {
  activity: AgendaActivity;
  title?: string | undefined;
}) {
  const code = activity.agendaItemId;
  return (
    <Link
      to="/drafts/$code"
      params={{ code }}
      className="flex items-center gap-2.5 rounded-md border border-border bg-card p-2.5"
    >
      <FolderOpen className="size-4 shrink-0 text-muted-foreground" />
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-1.5">
          <span className="mono-code text-sm font-semibold">{code}</span>
          <DraftBadge count={activity.unreadCount} important={activity.flUpdates > 0} />
        </span>
        <span className="block truncate text-xs text-muted-foreground">
          {title ? `${title} · ` : ""}
          {[
            activity.flUpdates ? `${activity.flUpdates} FL summary update(s)` : "",
            activity.newFiles ? `${activity.newFiles} new file(s)` : "",
            activity.newRounds ? `${activity.newRounds} new round(s)` : "",
            activity.newFolders - activity.newRounds > 0
              ? `${activity.newFolders - activity.newRounds} new folder(s)`
              : "",
            activity.flCount ? `${activity.flCount} FL summary(ies)` : "",
            activity.fileCount ? `${activity.fileCount} file(s)` : "",
          ]
            .filter(Boolean)
            .join(" · ") || "no files yet"}
        </span>
      </span>
      <span className="mono-code shrink-0 text-[11px] text-muted-foreground">
        {relativeTime(activity.latestAt ?? activity.latestFileAt)}
      </span>
    </Link>
  );
}
