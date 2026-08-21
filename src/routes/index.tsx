import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, WifiOff } from "lucide-react";
import { scheduleQueryOptions, minutesOf } from "@/services/schedule";
import { useMeetingClock } from "@/hooks/useMeetingClock";
import { SessionCard } from "@/components/SessionCard";
import { ChangesLink } from "@/components/AppShell";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "RAN1 Live — What's happening now at RAN1" },
      {
        name: "description",
        content:
          "Live, searchable RAN1 meeting schedule. See which sessions are running now, which room they are in, and what starts next.",
      },
      { property: "og:title", content: "RAN1 Live — What's happening now at RAN1" },
      {
        property: "og:description",
        content:
          "Live, searchable RAN1 meeting schedule built from the chair and sub-chair documents.",
      },
    ],
  }),
  component: NowPage,
});

function NowPage() {
  const { data, isLoading } = useQuery(scheduleQueryOptions);
  const bundle = data?.bundle;
  const clock = useMeetingClock(
    bundle?.meeting ?? {
      meetingId: "",
      meetingName: "",
      startDate: "",
      endDate: "",
      venue: "",
      city: "",
      timezone: "UTC",
      status: "upcoming",
    },
  );

  if (isLoading || !bundle) {
    return <p className="py-10 text-center text-sm text-muted-foreground">Loading schedule…</p>;
  }

  const dates = [...new Set(bundle.sessions.map((s) => s.date))].sort();
  const today = dates.includes(clock.localDate) ? clock.localDate : (dates[0] ?? "");
  const isToday = today === clock.localDate;
  const nowMin = isToday ? clock.nowMinutes : 0;

  const daySessions = bundle.sessions
    .filter((s) => s.date === today && s.kind !== "break" && s.kind !== "lunch")
    .sort((a, b) => a.startTime.localeCompare(b.startTime));

  const live = daySessions.filter(
    (s) => minutesOf(s.startTime) <= nowMin && minutesOf(s.endTime) > nowMin,
  );
  const next = daySessions.filter((s) => minutesOf(s.startTime) > nowMin).slice(0, 6);
  const latestChanges = [...bundle.changes]
    .sort((a, b) => b.detectedAt.localeCompare(a.detectedAt))
    .slice(0, 2);

  return (
    <div className="space-y-6">
      {data?.stale ? (
        <div className="flex items-start gap-2 rounded-md border border-warn/40 bg-warn/10 p-3 text-sm">
          <WifiOff className="mt-0.5 size-4 text-warn" />
          <div>
            <div className="font-medium">Showing cached schedule</div>
            <div className="text-xs text-muted-foreground">
              Last successful download {new Date(bundle.generatedAt).toLocaleTimeString()}
            </div>
          </div>
        </div>
      ) : null}

      <section>
        <div className="mb-2 flex items-baseline justify-between">
          <h1 className="text-lg font-semibold">Happening now</h1>
          <span className="mono-code text-sm text-muted-foreground tabular">
            {isToday ? clock.localTime : `${bundle.meeting.city} time`}
          </span>
        </div>
        {live.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
            No session running right now.
          </p>
        ) : (
          <div className="space-y-2">
            {live.map((s) => (
              <SessionCard key={s.sessionId} session={s} bundle={bundle} live />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">Starting next</h2>
        <div className="space-y-2">
          {next.length === 0 ? (
            <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
              Nothing else scheduled today.
            </p>
          ) : (
            next.map((s) => <SessionCard key={s.sessionId} session={s} bundle={bundle} compact />)
          )}
        </div>
      </section>

      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Latest changes</h2>
          <ChangesLink />
        </div>
        {latestChanges.map((c) => (
          <div key={c.changeId} className="rounded-lg border border-border bg-card p-3 text-sm">
            <div className="flex items-center gap-2">
              <AlertTriangle className="size-4 text-warn" />
              <span className="font-medium">{c.title}</span>
            </div>
            <div className="mono-code mt-1 text-xs text-muted-foreground">
              {c.from ? `${c.from} → ` : ""}
              {c.to}
            </div>
          </div>
        ))}
      </section>

      <Link
        to="/schedule"
        className="flex min-h-12 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground"
      >
        Open full timetable <ArrowRight className="size-4" />
      </Link>
    </div>
  );
}
