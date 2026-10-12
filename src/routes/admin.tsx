import { createFileRoute } from "@tanstack/react-router";
import { useActiveMeeting } from "@/hooks/useActiveMeeting";
import { useMeetingHealth } from "@/hooks/useMeetingHealth";
import { LoadingState, NoMeetingState } from "@/components/ScheduleStates";

export const Route = createFileRoute("/admin")({
  head: () => ({
    meta: [
      { title: "Ingestion status — RAN1 Live!" },
      {
        name: "description",
        content:
          "Health of the RAN1 Live! ingestion pipeline: discovered documents, parser confidence and unresolved source conflicts.",
      },
      { property: "og:title", content: "Ingestion status — RAN1 Live!" },
      {
        property: "og:description",
        content: "Documents, parser confidence and conflicts behind the published RAN1 schedule.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: AdminPage,
});

function AdminPage() {
  const { meeting, bundle, isLoading, origin } = useActiveMeeting();

  if (isLoading) return <LoadingState label="Loading ingestion status…" />;
  if (!meeting) return <NoMeetingState />;

  const lowConfidence = (bundle?.sources ?? []).filter((s) => (s.confidence ?? 1) < 0.8);
  const conflicts = (bundle?.conflicts ?? []).filter((c) => !c.resolved);

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h1 className="text-lg font-semibold">Ingestion status</h1>
        <p className="text-xs text-muted-foreground">
          {meeting.name} · served from the {origin === "meeting-local" ? "meeting-local" : "public"}{" "}
          source
        </p>
      </header>

      <HealthPanel slug={meeting.slug} />

      {!bundle ? (
        <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
          No schedule has been published for this meeting yet.
        </p>
      ) : (
        <>
          <section className="rounded-lg border border-border bg-card p-3 text-sm">
            <div className="font-medium capitalize">{bundle.ingest.state.replace(/_/g, " ")}</div>
            <p className="mono-code mt-1 text-xs text-muted-foreground">
              last success {new Date(bundle.ingest.lastSuccessfulAt).toLocaleString()}
              {bundle.ingest.lastAttemptAt
                ? ` · last attempt ${new Date(bundle.ingest.lastAttemptAt).toLocaleString()}`
                : ""}
            </p>
            {bundle.ingest.message ? (
              <p className="mt-1 text-xs text-muted-foreground">{bundle.ingest.message}</p>
            ) : null}
          </section>

          <section className="space-y-2">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Documents
            </h2>
            <ul className="space-y-1">
              {bundle.sources.map((s) => (
                <li
                  key={s.sourceId}
                  className="mono-code rounded-md border border-border bg-card p-2 text-[11px]"
                >
                  <span className="font-semibold text-foreground">{s.label}</span> · {s.type} ·{" "}
                  {s.origin} · confidence {Math.round((s.confidence ?? 1) * 100)}%
                  <span className="block truncate text-muted-foreground">{s.fileName}</span>
                </li>
              ))}
            </ul>
          </section>

          {lowConfidence.length > 0 ? (
            <section className="rounded-lg border border-warn/40 bg-warn/10 p-3 text-sm">
              <h2 className="font-semibold">Review queue</h2>
              <p className="text-xs text-muted-foreground">
                {lowConfidence.length} document(s) parsed with low confidence — their sessions are
                published but should be verified.
              </p>
            </section>
          ) : null}

          {conflicts.length > 0 ? (
            <section className="rounded-lg border border-warn/40 bg-warn/10 p-3 text-sm">
              <h2 className="font-semibold">Unresolved conflicts</h2>
              <ul className="mt-1 space-y-1 text-xs">
                {conflicts.map((c) => (
                  <li key={c.conflictId} className="mono-code">
                    {c.field}: {c.values.map((v) => `${v.sourceId}=${v.value}`).join("  vs  ")}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}

/**
 * What the refresh jobs last managed to do for this meeting, and what they
 * could not. The record is written by the updater itself (ingestion/health.py),
 * so a source that was silently skipped shows up here instead of going unnoticed.
 */
function HealthPanel({ slug }: { slug: string }) {
  const health = useMeetingHealth(slug);
  if (!health) return null;

  const warn = (health.warnings ?? []).filter((w) => w.level === "warn");
  const info = (health.warnings ?? []).filter((w) => w.level !== "warn");
  const sched = health.schedule;
  const drafts = health.drafts;
  const remote = health.remoteFtp;
  const when = (iso?: string) => (iso ? new Date(iso).toLocaleString() : "never");

  return (
    <section className="space-y-2 rounded-lg border border-border bg-card p-3 text-sm">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Pipeline health
        </h2>
        {health.updatedAt ? (
          <span className="mono-code text-[11px] text-muted-foreground">
            {when(health.updatedAt)}
          </span>
        ) : null}
      </div>

      <div className="mono-code grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[11px]">
        {sched ? (
          <>
            <span className="text-muted-foreground">Timetable</span>
            <span>
              {sched.sessionCount ?? 0} sessions · {sched.roomCount ?? 0} rooms ·{" "}
              {sched.sourceCount ?? 0} sources
            </span>
            <span className="text-muted-foreground">Rebuilt</span>
            <span>{when(sched.lastSuccessAt)}</span>
          </>
        ) : null}
        {drafts ? (
          <>
            <span className="text-muted-foreground">Drafts</span>
            <span>
              {drafts.artifactCount ?? 0} files · {drafts.readFolderCount ?? 0}/
              {drafts.folderCount ?? 0} folders read
            </span>
            <span className="text-muted-foreground">Scanned</span>
            <span>
              {when(drafts.lastSuccessAt)} · {drafts.source}
            </span>
          </>
        ) : null}
        {remote ? (
          <>
            <span className="text-muted-foreground">Remote server</span>
            <span>
              {remote.host ?? "not entered"} · {remote.state ?? "unknown"}
              {remote.credentials === false ? " · login missing" : ""}
            </span>
          </>
        ) : null}
      </div>

      {warn.length > 0 ? (
        <ul className="space-y-1 rounded-md border border-warn/40 bg-warn/10 p-2 text-xs">
          {warn.map((w) => (
            <li key={w.text} className="text-foreground">
              {w.text}
            </li>
          ))}
        </ul>
      ) : null}

      {info.length > 0 ? (
        <ul className="space-y-1 text-xs text-muted-foreground">
          {info.map((w) => (
            <li key={w.text}>{w.text}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
