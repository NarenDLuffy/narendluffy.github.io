import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight } from "lucide-react";
import { scheduleQueryOptions, minutesOf } from "@/services/schedule";
import { useMeetingClock } from "@/hooks/useMeetingClock";

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
    ],
  }),
  component: RoomsPage,
});

function RoomsPage() {
  const { data } = useQuery(scheduleQueryOptions);
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

  return (
    <div className="space-y-3">
      <h1 className="text-lg font-semibold">Rooms</h1>
      <p className="text-xs text-muted-foreground">{bundle.meeting.venue}</p>
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
                      : room.area ?? "No session running"}
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
