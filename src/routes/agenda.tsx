import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { CalendarPlus, Star, Trash2 } from "lucide-react";
import { scheduleQueryOptions, sessionMatchesAgenda } from "@/services/schedule";
import { useBookmarks } from "@/hooks/useBookmarks";
import { useMeetingClock } from "@/hooks/useMeetingClock";
import { buildIcs, downloadIcs } from "@/lib/ics";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/agenda")({
  head: () => ({
    meta: [
      { title: "My agenda — RAN1 Live" },
      {
        name: "description",
        content:
          "Follow RAN1 agenda items and get a personal meeting-week timeline you can export to your calendar.",
      },
      { property: "og:title", content: "My agenda — RAN1 Live" },
      {
        property: "og:description",
        content: "Your followed RAN1 agenda items as a personal timeline with ICS export.",
      },
    ],
  }),
  component: AgendaPage,
});

function AgendaPage() {
  const { data } = useQuery(scheduleQueryOptions);
  const { bookmarks, toggle, clear, isBookmarked } = useBookmarks();
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

  if (!bundle) return <p className="py-10 text-center text-sm text-muted-foreground">Loading…</p>;

  const mine = bundle.sessions
    .filter((s) => s.kind !== "break" && s.kind !== "lunch")
    .filter((s) => bookmarks.length > 0 && sessionMatchesAgenda(s, bookmarks))
    .sort((a, b) => (a.date + a.startTime).localeCompare(b.date + b.startTime));

  const byDay = mine.reduce<Record<string, typeof mine>>((acc, s) => {
    (acc[s.date] ??= []).push(s);
    return acc;
  }, {});

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h1 className="text-lg font-semibold">My agenda</h1>
        <p className="text-xs text-muted-foreground">
          Bookmarks are stored on this device. Sign-in sync arrives with company features.
        </p>
      </header>

      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Follow agenda items
        </h2>
        <div className="flex flex-wrap gap-1.5">
          {bundle.agendaItems.map((a) => (
            <button
              key={a.code}
              type="button"
              onClick={() => toggle(a.code)}
              title={a.title}
              className={cn(
                "mono-code inline-flex min-h-9 items-center gap-1 rounded-md border px-2.5 text-xs font-medium",
                isBookmarked(a.code)
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-card text-muted-foreground",
              )}
            >
              {isBookmarked(a.code) ? <Star className="size-3 fill-current" /> : null}
              {a.code}
            </button>
          ))}
        </div>
      </section>

      {mine.length > 0 ? (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => downloadIcs(buildIcs(bundle, mine), `${bundle.meeting.meetingName}-my-agenda.ics`)}
            className="inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-md bg-primary px-3 text-sm font-semibold text-primary-foreground"
          >
            <CalendarPlus className="size-4" /> Export .ics
          </button>
          <button
            type="button"
            onClick={clear}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-muted-foreground"
          >
            <Trash2 className="size-4" /> Clear
          </button>
        </div>
      ) : null}

      {mine.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
          Star agenda items above (or on any session) to build your personal timeline.
        </p>
      ) : (
        Object.entries(byDay).map(([date, sessions]) => (
          <section key={date}>
            <h2 className="mb-2 text-sm font-semibold">
              {sessions[0]?.day}
              <span className="mono-code ml-2 text-xs text-muted-foreground">{date}</span>
              {date === clock.localDate ? (
                <span className="ml-2 rounded bg-live/15 px-1.5 py-0.5 text-[10px] font-bold uppercase text-live">
                  today
                </span>
              ) : null}
            </h2>
            <ol className="space-y-1.5">
              {sessions.map((s) => (
                <li key={s.sessionId}>
                  <Link
                    to="/rooms/$roomId"
                    params={{ roomId: s.roomId }}
                    className="flex items-center gap-3 rounded-md border border-border bg-card p-2.5"
                  >
                    <span className="mono-code w-12 shrink-0 text-sm font-semibold tabular">
                      {s.startTime}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium">
                        {s.topic}
                        {s.agendaItems.length ? (
                          <span className="mono-code ml-1.5 text-xs text-muted-foreground">
                            {s.agendaItems.join(" · ")}
                          </span>
                        ) : null}
                      </span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {s.roomName}
                      </span>
                    </span>
                  </Link>
                </li>
              ))}
            </ol>
          </section>
        ))
      )}
    </div>
  );
}
