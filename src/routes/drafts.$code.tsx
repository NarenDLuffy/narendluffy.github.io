import { createFileRoute, useParams } from "@tanstack/react-router";
import { useEffect, useMemo } from "react";
import { ExternalLink, FolderOpen } from "lucide-react";
import { useActiveMeeting } from "@/hooks/useActiveMeeting";
import { useDrafts } from "@/hooks/useDrafts";
import { LoadingState, NoMeetingState } from "@/components/ScheduleStates";
import { ArtifactRow, EventRow, FollowButton } from "@/components/DraftActivity";
import { artifactsForAgenda, foldersById, relativeTime } from "@/services/draftService";

export const Route = createFileRoute("/drafts/$code")({
  head: ({ params }) => ({
    meta: [
      { title: `Drafts for agenda item ${params.code} — RAN1 Live` },
      {
        name: "description",
        content: `Drafts, feature lead summaries and upload history for RAN1 agenda item ${params.code}.`,
      },
      { property: "og:title", content: `Drafts for agenda item ${params.code} — RAN1 Live` },
      {
        property: "og:description",
        content: `Every draft and FL summary uploaded for RAN1 agenda item ${params.code}.`,
      },
      { property: "og:type", content: "article" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: DraftDetailPage,
});

function DraftDetailPage() {
  const { code } = useParams({ from: "/drafts/$code" });
  const { meeting, bundle, isLoading } = useActiveMeeting();
  const drafts = useDrafts(meeting);
  const markSeenFn = drafts.markSeen;

  useEffect(() => {
    if (meeting) markSeenFn(code);
  }, [code, meeting, markSeenFn]);

  const item = bundle?.agendaItems.find((a) => a.code === code);
  const activity = drafts.activity.get(code);
  const index = drafts.index;

  const artifacts = useMemo(
    () => (index ? artifactsForAgenda(index, code) : []),
    [index, code],
  );
  const folders = useMemo(() => {
    if (!index) return [];
    const map = foldersById(index);
    const ids = new Set(artifacts.map((a) => a.folderId));
    index.folders.filter((f) => f.agendaItemId === code).forEach((f) => ids.add(f.id));
    return [...ids].map((id) => map.get(id)).filter(Boolean);
  }, [index, artifacts, code]);

  if (isLoading) return <LoadingState label="Loading drafts…" />;
  if (!meeting) return <NoMeetingState />;

  const flSummaries = artifacts.filter((a) => a.fileType === "fl_summary");
  const others = artifacts.filter((a) => a.fileType !== "fl_summary");

  return (
    <div className="space-y-5">
      <header className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="mono-code text-lg font-semibold">{code}</h1>
            <p className="text-xs text-muted-foreground">{item?.title ?? "Agenda item"}</p>
          </div>
          <FollowButton
            following={drafts.isFollowing(code)}
            onClick={() => drafts.toggleFollow(code)}
          />
        </div>
        <p className="text-xs text-muted-foreground">
          {artifacts.length} file(s) · {flSummaries.length} FL summary document(s)
          {activity?.latestAt ? ` · last change ${relativeTime(activity.latestAt)}` : ""}
        </p>
      </header>

      {folders.length > 0 ? (
        <section>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Folders
          </h2>
          <ul className="space-y-1.5">
            {folders.map((f) =>
              f ? (
                <li key={f.id}>
                  <a
                    href={f.url ?? "#"}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-2 rounded-md border border-border bg-card p-2.5 text-sm"
                  >
                    <FolderOpen className="size-4 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 flex-1 truncate">{f.name}</span>
                    <span className="mono-code shrink-0 text-[11px] text-muted-foreground">
                      {f.fileCount} file(s)
                    </span>
                    <ExternalLink className="size-3.5 shrink-0 text-muted-foreground" />
                  </a>
                </li>
              ) : null,
            )}
          </ul>
        </section>
      ) : null}

      {flSummaries.length > 0 ? (
        <section>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            FL summaries
          </h2>
          <ol className="space-y-1.5">
            {flSummaries.map((a) => (
              <li key={a.id}>
                <ArtifactRow artifact={a} />
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Drafts
        </h2>
        {others.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border p-3 text-xs text-muted-foreground">
            No drafts indexed for this agenda item yet.
          </p>
        ) : (
          <ol className="space-y-1.5">
            {others.map((a) => (
              <li key={a.id}>
                <ArtifactRow artifact={a} />
              </li>
            ))}
          </ol>
        )}
      </section>

      {activity && activity.events.length > 0 ? (
        <section>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            History
          </h2>
          <ol className="space-y-1.5">
            {activity.events.map((e) => (
              <li key={e.id}>
                <EventRow event={e} />
              </li>
            ))}
          </ol>
        </section>
      ) : null}
    </div>
  );
}
