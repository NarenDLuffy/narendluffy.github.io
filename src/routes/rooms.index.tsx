import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronRight } from "lucide-react";
import { minutesOf } from "@/services/scheduleService";
import { useActiveMeeting } from "@/hooks/useActiveMeeting";
import { MeetingBanner } from "@/components/MeetingBanner";
import { LoadingState, NoMeetingState, NoScheduleState } from "@/components/ScheduleStates";

export const Route = createFileRoute("/rooms/")({
  head: () => ({
    meta: [
      { title: "Rooms — RAN1 Live" },
      {
        name: "description",
        content: "Every RAN1 meeting room with what is running now and what comes next.",
      },
      { property: "og:title", content: "RAN1 meeting rooms — RAN1 Live" },
      {
        property: "og:description",
        content: "Room-by-room view of the RAN1 meeting week: now, next and session leads.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: RoomsPage,
});

function RoomsPage() {
  const { meeting, bundle, stale, isCurrent, isLoading, clock } = useActiveMeeting();

  if (isLoading) return <LoadingState label="Loading rooms…" />;
  if (!meeting) return <NoMeetingState />;

  const banner = (
    <MeetingBanner meeting={meeting} bundle={bundle} stale={stale} isCurrent={isCurrent} />
  );

  if (!bundle || bundle.rooms.length === 0) {
    return (
      <div className="space-y-4">
        {banner}
        <NoScheduleState meeting={meeting} />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {banner}
      <h1 className="text-lg font-semibold">Rooms</h1>
      <p className="text-xs text-muted-foreground">{meeting.venue ?? meeting.city ?? ""}</p>
      <ul className="space-y-2">
        {bundle.rooms.map((room) => {
          const todays = bundle.sessions.filter(
            (s) => s.roomId === room.roomId && s.date === clock.localDate,
          );
          const live = todays.find(
            (s) =>
              minutesOf(s.startTime) <= clock.nowMinutes &&
              minutesOf(s.endTime) > clock.nowMinutes,
          );
          return (
            <li key={room.roomId}>
              <Link
                to="/rooms/$roomId"
                params={{ roomId: room.roomId }}
                className="flex items-center gap-3 rounded-lg border border-border bg-card p-3"
              >
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium">{room.roomName}</span>
                  <span className="block truncate text-xs text-muted-foreground">
                    {live
                      ? `Now: ${live.topic}${live.agendaItems.length ? ` · ${live.agendaItems.join(", ")}` : ""}`
                      : (room.floor ?? room.description ?? "No session running")}
                  </span>
                </span>
                <ChevronRight className="size-4 text-muted-foreground" />
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
