import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { z } from "zod";
import { CalendarPlus, Crosshair, Search, X } from "lucide-react";
import type { Session } from "@/types/schedule";
import { SessionDetailSheet } from "@/components/SessionDetailSheet";
import { RefreshButton } from "@/components/RefreshButton";
import { useDeadlines } from "@/hooks/useDeadlines";
import { activeRooms } from "@/lib/rooms";
import { buildIcs, downloadIcs } from "@/lib/ics";

import { meetingDates, sessionMatchesAgenda, searchSession } from "@/services/scheduleService";
import { useActiveMeeting } from "@/hooks/useActiveMeeting";
import { DayTabs } from "@/components/DayTabs";
import { Timetable } from "@/components/Timetable";
import { useBookmarks } from "@/hooks/useBookmarks";
import { SourcePanel } from "@/components/SourcePanel";
import { MeetingBanner } from "@/components/MeetingBanner";
import { LoadingState, NoMeetingState, NoScheduleState } from "@/components/ScheduleStates";
import { cn } from "@/lib/utils";

const searchSchema = z.object({
  day: z.string().optional(),
  ai: z.string().optional(),
  q: z.string().optional(),
  room: z.string().optional(),
  hide: z.coerce.boolean().optional(),
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
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: SchedulePage,
});

function SchedulePage() {
  const { meeting, bundle, stale, isCurrent, isLoading, origin, clock } = useActiveMeeting();
  const search = Route.useSearch();
  const navigate = useNavigate({ from: "/schedule" });
  const [nowKey, setNowKey] = useState(0);
  const { bookmarks } = useBookmarks();
  const [selected, setSelected] = useState<Session | null>(null);
  const { deadlines } = useDeadlines(meeting?.id);

  if (isLoading) return <LoadingState label="Loading timetable…" />;
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

  const isBreak = (s: Session) => s.kind === "break" || s.kind === "lunch";
  const matches = (s: Session) => isBreak(s) || (sessionMatchesAgenda(s, filters) && searchSession(s, q));
  const filtering = filters.length > 0 || Boolean(q.trim());
  const dayAll = bundle.sessions.filter((s) => s.date === day);
  const sessions = dayAll.filter(matches);
  // Filtered view keeps every block in place and greys out the rest, unless
  // "Hide others" is on.
  const shown = filtering && !search.hide ? dayAll : sessions;

  const topLevel = [...new Set(bundle.agendaItems.filter((a) => !a.parent).map((a) => a.code))];

  return (
    <div className="space-y-3">
      {banner}

      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={q}
            onChange={(e) => setSearch({ q: e.target.value || undefined })}
            placeholder="Search topic, room, agenda item, lead"
            className="min-h-11 w-full rounded-md border border-input bg-card pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <button
          type="button"
          onClick={() =>
            downloadIcs(
              buildIcs(
                bundle,
                sessions.filter((s) => !isBreak(s)),
                deadlines,
              ),
              `${meeting.slug}-${day}.ics`,
            )
          }
          disabled={sessions.length === 0}
          className="inline-flex min-h-11 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-sm font-semibold disabled:opacity-50"
          title="Export the sessions currently shown to your calendar"
        >
          <CalendarPlus className="size-4" />
          Export
        </button>
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


      <RefreshButton meeting={meeting} bundle={bundle} />

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
        {filtering ? (
          <label className="ml-auto inline-flex min-h-9 items-center gap-1.5 text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={Boolean(search.hide)}
              onChange={(e) => setSearch({ hide: e.target.checked || undefined })}
            />
            Hide others
          </label>
        ) : null}
      </div>

      <Timetable
        rooms={activeRooms(bundle)}
        sessions={shown}
        isMatch={filtering && !search.hide ? matches : undefined}
        onSelect={setSelected}
        nowMinutes={clock.nowMinutes}
        showNowMarker={day === clock.localDate}
        scrollToNowKey={nowKey}
      />

      <SessionDetailSheet
        bundle={bundle}
        session={selected}
        onOpenChange={(open) => !open && setSelected(null)}
      />

      <SourcePanel bundle={bundle} meeting={meeting} origin={origin} />
    </div>
  );
}
