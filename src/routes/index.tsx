import { createFileRoute, Link } from "@tanstack/react-router";
import { AlertTriangle, ArrowRight } from "lucide-react";
import { minutesOf } from "@/services/scheduleService";
import { useActiveMeeting } from "@/hooks/useActiveMeeting";
import { SessionCard } from "@/components/SessionCard";
import { ChangesLink } from "@/components/AppShell";
import { MeetingBanner } from "@/components/MeetingBanner";
import { LoadingState, NoMeetingState, NoScheduleState } from "@/components/ScheduleStates";

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
          "Live, searchable RAN1 meeting schedule built automatically from the published meeting documents.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: NowPage,
});

function NowPage() {
  const { meeting, bundle, stale, isCurrent, isLoading, clock } = useActiveMeeting();

  if (isLoading) return <LoadingState />;
  if (!meeting) return <NoMeetingState />;

  const banner = (
    <MeetingBanner meeting={meeting} bundle={bundle} stale={stale} isCurrent={isCurrent} />
  );

  if (!bundle || bundle.sessions.length === 0) {
    return (
      <div className="space-y-4">
        {banner}
        <NoScheduleState meeting={meeting} />
      </div>
    );
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
      {banner}

      <section>
        <div className="mb-2 flex items-baseline justify-between">
          <h1 className="text-lg font-semibold">
            {isToday ? "Happening now" : `Day plan · ${daySessions[0]?.day ?? today}`}
          </h1>
          <span className="mono-code text-sm text-muted-foreground tabular">
            {isToday ? clock.localTime : `${meeting.city ?? "meeting"} time`}
          </span>
        </div>
        {live.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
            {isToday ? "No session running right now." : "Not a meeting day."}
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
        <h2 className="mb-2 text-lg font-semibold">{isToday ? "Starting next" : "Sessions"}</h2>
        <div className="space-y-2">
          {next.length === 0 ? (
            <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
              Nothing else scheduled.
            </p>
          ) : (
            next.map((s) => <SessionCard key={s.sessionId} session={s} bundle={bundle} compact />)
          )}
        </div>
      </section>

      {latestChanges.length > 0 ? (
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
      ) : null}

      <Link
        to="/schedule"
        className="flex min-h-12 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground"
      >
        Open full timetable <ArrowRight className="size-4" />
      </Link>
    </div>
  );
}
