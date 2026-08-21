import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { z } from "zod";
import { Crosshair, Search, X } from "lucide-react";
import {
  scheduleQueryOptions,
  meetingDates,
  sessionMatchesAgenda,
  searchSession,
} from "@/services/schedule";
import { useMeetingClock } from "@/hooks/useMeetingClock";
import { DayTabs } from "@/components/DayTabs";
import { Timetable } from "@/components/Timetable";
import { useBookmarks } from "@/hooks/useBookmarks";
import { SourcePanel } from "@/components/SourcePanel";
import { cn } from "@/lib/utils";

const searchSchema = z.object({
  day: z.string().optional(),
  ai: z.string().optional(),
  q: z.string().optional(),
  room: z.string().optional(),
});

export const Route = createFileRoute("/schedule")({
  validateSearch: searchSchema,
  head: () => ({
    meta: [
      { title: "Timetable — RAN1 Live" },
      {
        name: "description",
        content:
          "Full RAN1 week timetable by room and time, with agenda-item filtering and a live current-time marker.",
      },
      { property: "og:title", content: "RAN1 timetable — RAN1 Live" },
      {
        property: "og:description",
        content: "Room-by-room RAN1 timetable with agenda-item filters you can share by URL.",
      },
    ],
  }),
  component: SchedulePage,
});

function SchedulePage() {
  const { data, isLoading } = useQuery(scheduleQueryOptions);
  const search = Route.useSearch();
  const navigate = useNavigate({ from: "/schedule" });
  const [nowKey, setNowKey] = useState(0);
  const { bookmarks } = useBookmarks();
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
    return <p className="py-10 text-center text-sm text-muted-foreground">Loading timetable…</p>;
  }

  const days = meetingDates(bundle);
  const fallbackDay = days.some((d) => d.date === clock.localDate)
    ? clock.localDate
    : (days[0]?.date ?? "");
  const day = search.day ?? fallbackDay;
  const filters = search.ai ? search.ai.split(",").filter(Boolean) : [];
  const q = search.q ?? "";

  const setSearch = (patch: Partial<z.infer<typeof searchSchema>>) =>
    navigate({ search: (prev) => ({ ...prev, ...patch }), replace: true });

  const toggleFilter = (code: string) => {
    const next = filters.includes(code) ? filters.filter((c) => c !== code) : [...filters, code];
    setSearch({ ai: next.length ? next.join(",") : undefined });
  };

  const sessions = bundle.sessions
    .filter((s) => s.date === day)
    .filter((s) => s.kind === "break" || s.kind === "lunch" || sessionMatchesAgenda(s, filters))
    .filter((s) => searchSession(s, q));

  const topLevel = [...new Set(bundle.agendaItems.filter((a) => !a.parent).map((a) => a.code))];

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={q}
            onChange={(e) => setSearch({ q: e.target.value || undefined })}
            placeholder="Search topic, room, AI, lead"
            className="min-h-11 w-full rounded-md border border-input bg-card pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <button
          type="button"
          onClick={() => {
            setSearch({ day: undefined });
            setNowKey((k) => k + 1);
          }}
          className="inline-flex min-h-11 items-center gap-1.5 rounded-md bg-primary px-3 text-sm font-semibold text-primary-foreground"
        >
          <Crosshair className="size-4" />
          Now
        </button>
      </div>

      <DayTabs days={days} value={day} onChange={(d) => setSearch({ day: d })} />

      <div className="flex flex-wrap items-center gap-1.5">
        {topLevel.map((code) => (
          <button
            key={code}
            type="button"
            onClick={() => toggleFilter(code)}
            className={cn(
              "mono-code min-h-9 rounded-md border px-2.5 text-xs font-medium",
              filters.includes(code)
                ? "border-primary bg-primary/10 text-primary"
                : "border-border bg-card text-muted-foreground",
            )}
          >
            {code}
          </button>
        ))}
        {bookmarks.length > 0 ? (
          <button
            type="button"
            onClick={() => setSearch({ ai: bookmarks.join(",") })}
            className="min-h-9 rounded-md border border-border bg-card px-2.5 text-xs font-medium"
          >
            My agenda items
          </button>
        ) : null}
        {filters.length > 0 || q ? (
          <button
            type="button"
            onClick={() => setSearch({ ai: undefined, q: undefined })}
            className="inline-flex min-h-9 items-center gap-1 rounded-md border border-border px-2.5 text-xs text-muted-foreground"
          >
            <X className="size-3.5" /> Clear
          </button>
        ) : null}
      </div>

      <Timetable
        rooms={bundle.rooms}
        sessions={sessions}
        nowMinutes={clock.nowMinutes}
        showNowMarker={day === clock.localDate}
        scrollToNowKey={nowKey}
      />

      <SourcePanel bundle={bundle} origin={data?.origin ?? "public"} />
    </div>
  );
}
