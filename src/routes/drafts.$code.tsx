import { createFileRoute, useParams } from "@tanstack/react-router";
import { useEffect, useMemo } from "react";
import { DraftBreadcrumbs, DraftTree } from "@/components/DraftTree";
import { useActiveMeeting } from "@/hooks/useActiveMeeting";
import { useDrafts } from "@/hooks/useDrafts";
import { LoadingState, NoMeetingState } from "@/components/ScheduleStates";
import { ArtifactRow, EventRow, FollowButton } from "@/components/DraftActivity";
import {
  artifactsForAgenda,
  buildDraftTree,
  latestFlSummary,
  relativeTime,
} from "@/services/draftService";

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
  // Whatever structure exists on the server, rendered as-is: rounds, custom
  // folders, deep nesting or plain files sitting in the agenda folder.
  const tree = useMemo(() => (index ? buildDraftTree(index, code) : []), [index, code]);
  const treeFolderPaths = useMemo(() => {
    const paths = new Set<string>();
    const walk = (nodes: typeof tree) =>
      nodes.forEach((n) => {
        paths.add(n.folder.normalizedPath);
        walk(n.children);
      });
    walk(tree);
    return paths;
  }, [tree]);
  const looseFiles = useMemo(
    () => artifacts.filter((a) => !treeFolderPaths.has(a.folderPath ?? "")),
    [artifacts, treeFolderPaths],
  );
  const latestFl = useMemo(
    () => (index ? latestFlSummary(index, code) : undefined),
    [index, code],
  );

  if (isLoading) return <LoadingState label="Loading drafts…" />;
  if (!meeting) return <NoMeetingState />;

  const flSummaries = artifacts.filter((a) => a.fileType === "fl_summary");
  const unread = activity?.unread ?? [];
  const unreadCounts = {
    files: unread.filter((e) => e.eventType === "NEW_FILE").length,
    updated: unread.filter((e) => e.eventType === "FILE_UPDATED").length,
    folders: unread.filter((e) => e.eventType === "NEW_FOLDER").length,
    fl: unread.filter((e) => e.semanticType === "FL_SUMMARY_UPDATED").length,
  };

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

      {unread.length > 0 ? (
        <section className="rounded-lg border border-primary/30 bg-primary/5 p-3">
          <h2 className="text-sm font-semibold">Since you last looked</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            {[
              unreadCounts.files ? `${unreadCounts.files} new file(s)` : "",
              unreadCounts.updated ? `${unreadCounts.updated} updated file(s)` : "",
              unreadCounts.folders ? `${unreadCounts.folders} new folder(s)` : "",
              unreadCounts.fl ? `${unreadCounts.fl} FL summary update(s)` : "",
            ]
              .filter(Boolean)
              .join(" · ")}{" "}
            — anywhere below this agenda item.
          </p>
        </section>
      ) : null}

      {latestFl ? (
        <section>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Latest FL summary
          </h2>
          <DraftBreadcrumbs trail={(latestFl.folderPath ?? "").split("/").filter(Boolean)} />
          <div className="mt-1.5">
            <ArtifactRow artifact={latestFl} />
          </div>
        </section>
      ) : null}

      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Drafts
        </h2>
        <DraftTree nodes={tree} looseFiles={looseFiles} />
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
