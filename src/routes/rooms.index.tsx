import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronRight } from "lucide-react";
import { minutesOf } from "@/services/scheduleService";
import { useActiveMeeting } from "@/hooks/useActiveMeeting";
import { MeetingBanner } from "@/components/MeetingBanner";
import { LoadingState, NoMeetingState, NoScheduleState } from "@/components/ScheduleStates";
import { RefreshButton } from "@/components/RefreshButton";
import { activeRooms, roomLabel, roomStyle } from "@/lib/rooms";

export const Route = createFileRoute("/rooms/")({
  head: () => ({
    meta: [
      { title: "Rooms — RAN1 Live!" },
      {
        name: "description",
        content: "Every RAN1 meeting room with what is running now and what comes next.",
      },
      { property: "og:title", content: "RAN1 meeting rooms — RAN1 Live!" },
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

  if (!bundle || activeRooms(bundle).length === 0) {
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
      <RefreshButton meeting={meeting} bundle={bundle} />
      <p className="text-xs text-muted-foreground">{meeting.venue ?? meeting.city ?? ""}</p>
      <ul className="space-y-2">
        {activeRooms(bundle).map((room) => {
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
                style={roomStyle(room)}
                className="flex items-center gap-3 rounded-lg border border-l-4 border-border border-l-[var(--room-color)] bg-card p-3"
              >
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium">{roomLabel(room)}</span>
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
