import { useMemo, useState } from "react";
import { buildThreads, type DraftThread } from "@/lib/draftThreads";
import { relativeTime } from "@/services/draftService";
import { cn } from "@/lib/utils";
import type { DraftArtifact } from "@/types/drafts";

/** Discussion threads: one row per draft, a dot per version along the day. */
export function DraftThreads({ artifacts }: { artifacts: DraftArtifact[] }) {
  const threads = useMemo(() => buildThreads(artifacts).filter((t) => t.versions.length > 1 || t.isSummary), [artifacts]);
  const [showAll, setShowAll] = useState(false);
  if (threads.length === 0) return null;
  const times = threads.flatMap((t) => t.versions.map((v) => Date.parse(v.at))).filter(Number.isFinite);
  const min = Math.min(...times);
  const span = Math.max(1, Math.max(...times) - min);
  const shown = showAll ? threads : threads.slice(0, 6);
  return (
    <section>
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Activity</h2>
      <ol className="space-y-2">
        {shown.map((t) => (
          <ThreadRow key={t.key} thread={t} min={min} span={span} />
        ))}
      </ol>
      {threads.length > 6 ? (
        <button type="button" className="mt-2 text-xs font-medium text-primary" onClick={() => setShowAll((s) => !s)}>
          {showAll ? "Show fewer" : `Show all ${threads.length} threads`}
        </button>
      ) : null}
    </section>
  );
}

function ThreadRow({ thread, min, span }: { thread: DraftThread; min: number; span: number }) {
  const l = thread.latest;
  let summaryN = 0;
  return (
    <li className="rounded-lg border border-border bg-card p-2.5">
      <div className="flex items-baseline justify-between gap-2">
        <a href={l.artifact.sources[0]?.url ?? "#"} target="_blank" rel="noreferrer" className="min-w-0 truncate text-sm font-medium hover:underline">
          {thread.title}
        </a>
        <span className="shrink-0 text-[11px] text-muted-foreground">{relativeTime(l.at)}</span>
      </div>
      <p className="text-[11px] text-muted-foreground">
        v{l.version.join(".")}{l.author ? ` · ${l.author}` : ""} · {thread.versions.length} version(s)
      </p>
      <div className="relative mt-2 h-3 rounded-full bg-secondary" aria-hidden>
        {thread.versions.map((v, i) => {
          const left = ((Date.parse(v.at) - min) / span) * 100;
          const summary = thread.isSummary;
          if (summary) summaryN += 1;
          return (
            <span
              key={v.artifact.id}
              title={`${summary ? `Summary #${summaryN} · ` : ""}v${v.version.join(".")}${v.author ? ` · ${v.author}` : ""}`}
              className={cn(
                "absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-background",
                summary ? "bg-primary" : i === thread.versions.length - 1 ? "bg-live" : "bg-muted-foreground",
              )}
              style={{ left: `${Number.isFinite(left) ? left : 100}%` }}
            />
          );
        })}
      </div>
    </li>
  );
}
