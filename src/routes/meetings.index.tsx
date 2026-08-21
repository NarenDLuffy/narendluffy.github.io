import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, ChevronRight, CircleDot, Clock3 } from "lucide-react";
import { meetingIndexQueryOptions, formatDateRange, selectCurrentMeeting } from "@/services/meetingService";
import { setSelectedMeetingId } from "@/services/meetingSelection";
import { useActiveMeeting } from "@/hooks/useActiveMeeting";
import type { MeetingStatus } from "@/types/meeting";
import { LoadingState, NoMeetingState } from "@/components/ScheduleStates";

const STATUS: Record<MeetingStatus, { label: string; icon: typeof CircleDot; className: string }> = {
  active: { label: "In progress", icon: CircleDot, className: "text-live" },
  upcoming: { label: "Upcoming", icon: Clock3, className: "text-primary" },
  completed: { label: "Archived", icon: CheckCircle2, className: "text-muted-foreground" },
};

export const Route = createFileRoute("/meetings/")({
  head: () => ({
    meta: [
      { title: "Meetings & archive — RAN1 Live" },
      {
        name: "description",
        content:
          "Every discovered 3GPP RAN1 meeting: the one in progress, the next one, and the archive of past meeting weeks.",
      },
      { property: "og:title", content: "RAN1 meetings & archive — RAN1 Live" },
      {
        property: "og:description",
        content: "Switch between RAN1 meeting weeks; new meetings appear automatically.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: MeetingsPage,
});

function MeetingsPage() {
  const { data, isLoading } = useQuery(meetingIndexQueryOptions);
  const { meeting: activeMeeting } = useActiveMeeting();
  const navigate = useNavigate();

  if (isLoading) return <LoadingState label="Discovering meetings…" />;

  const meetings = data?.meetings ?? [];
  if (meetings.length === 0) return <NoMeetingState />;

  const current = selectCurrentMeeting(meetings);
  const groups: { title: string; items: typeof meetings }[] = [
    { title: "In progress", items: meetings.filter((m) => m.status === "active") },
    { title: "Upcoming", items: meetings.filter((m) => m.status === "upcoming") },
    { title: "Archive", items: meetings.filter((m) => m.status === "completed") },
  ].filter((g) => g.items.length > 0);

  const open = (id: string) => {
    setSelectedMeetingId(current && id === current.id ? "" : id);
    navigate({ to: "/" });
  };

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h1 className="text-lg font-semibold">Meetings</h1>
        <p className="text-xs text-muted-foreground">
          Discovered automatically from the 3GPP server. The app follows the current meeting on its
          own; pick another one to browse its archive.
        </p>
      </header>

      {groups.map((group) => (
        <section key={group.title} className="space-y-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            {group.title}
          </h2>
          <ul className="space-y-2">
            {group.items.map((m) => {
              const s = STATUS[m.status];
              const Icon = s.icon;
              return (
                <li key={m.id}>
                  <button
                    type="button"
                    onClick={() => open(m.id)}
                    className="flex w-full items-center gap-3 rounded-lg border border-border bg-card p-3 text-left"
                  >
                    <Icon className={`size-4 shrink-0 ${s.className}`} />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium">
                        {m.name}
                        {activeMeeting?.id === m.id ? (
                          <span className="ml-2 rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-bold uppercase text-primary">
                            viewing
                          </span>
                        ) : null}
                      </span>
                      <span className="mono-code block truncate text-xs text-muted-foreground">
                        {formatDateRange(m.startDate, m.endDate)}
                        {m.city ? ` · ${m.city}` : ""}
                        {m.type !== "regular" ? ` · ${m.type}` : ""}
                      </span>
                    </span>
                    <ChevronRight className="size-4 text-muted-foreground" />
                  </button>
                  <Link
                    to="/meetings/$meetingSlug"
                    params={{ meetingSlug: m.slug }}
                    className="mono-code mt-1 inline-block px-1 text-[11px] text-muted-foreground underline underline-offset-2"
                  >
                    details
                  </Link>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
