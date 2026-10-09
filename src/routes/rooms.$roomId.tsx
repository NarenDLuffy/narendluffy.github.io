import { roomLabel, roomStyle } from "@/lib/rooms";
import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, MapPin, Users } from "lucide-react";
import { minutesOf } from "@/services/scheduleService";
import { useActiveMeeting } from "@/hooks/useActiveMeeting";
import { useCompanyPresence } from "@/hooks/useCompanyPresence";
import { SessionCard } from "@/components/SessionCard";
import { LoadingState, NoMeetingState, NoScheduleState } from "@/components/ScheduleStates";

export const Route = createFileRoute("/rooms/$roomId")({
  head: () => ({
    meta: [
      { title: "Room — RAN1 Live" },
      {
        name: "description",
        content: "What is running now and next in this RAN1 meeting room, plus the full day plan.",
      },
      { property: "og:title", content: "Room schedule — RAN1 Live" },
      {
        property: "og:description",
        content: "Now, next and the full day plan for a single RAN1 meeting room.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: RoomPage,
});

function RoomPage() {
  const { roomId } = Route.useParams();
  const { meeting, bundle, isLoading, clock } = useActiveMeeting();
  const { joined, presence, myRoomId, enter, exit } = useCompanyPresence(meeting?.id);

  if (isLoading) return <LoadingState label="Loading room…" />;
  if (!meeting) return <NoMeetingState />;
  if (!bundle) return <NoScheduleState meeting={meeting} />;

  const room = bundle.rooms.find((r) => r.roomId === roomId);
  if (!room) {
    return (
      <div className="py-10 text-center text-sm text-muted-foreground">
        Unknown room.{" "}
        <Link to="/rooms" className="underline">
          Back to rooms
        </Link>
      </div>
    );
  }

  const dates = [...new Set(bundle.sessions.map((s) => s.date))].sort();
  const day = dates.includes(clock.localDate) ? clock.localDate : (dates[0] ?? "");
  const todays = bundle.sessions
    .filter((s) => s.roomId === roomId && s.date === day)
    .sort((a, b) => a.startTime.localeCompare(b.startTime));
  const isToday = day === clock.localDate;
  const live = isToday
    ? todays.find(
        (s) =>
          minutesOf(s.startTime) <= clock.nowMinutes && minutesOf(s.endTime) > clock.nowMinutes,
      )
    : undefined;
  const next = todays.find((s) => minutesOf(s.startTime) > (isToday ? clock.nowMinutes : -1));
  const here = presence.filter((p) => p.roomId === roomId);
  const iAmHere = myRoomId === roomId;

  return (
    <div className="space-y-5">
      <Link to="/rooms" className="inline-flex items-center gap-1 text-sm text-muted-foreground">
        <ArrowLeft className="size-4" /> Rooms
      </Link>

      <header>
        <h1 style={roomStyle(room)} className="flex items-center gap-2 text-xl font-semibold"><span className="size-3 rounded-full bg-[var(--room-color)]" aria-hidden />{roomLabel(room)}</h1>
        <p className="flex items-center gap-1 text-xs text-muted-foreground">
          <MapPin className="size-3.5" />
          {room.floor ? `${room.floor} · ` : ""}
          {meeting.venue ?? meeting.city ?? meeting.name}
        </p>
      </header>

      <section className="space-y-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Now</h2>
        {live ? (
          <SessionCard session={live} bundle={bundle} live />
        ) : (
          <p className="rounded-lg border border-dashed border-border p-3 text-sm text-muted-foreground">
            No session running in this room.
          </p>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Next
        </h2>
        {next ? (
          <SessionCard session={next} bundle={bundle} compact />
        ) : (
          <p className="rounded-lg border border-dashed border-border p-3 text-sm text-muted-foreground">
            Nothing else scheduled here today.
          </p>
        )}
      </section>

      <RoomColleagues meetingId={meeting.id} roomId={room.roomId} sessionId={live?.sessionId} />

      <section className="space-y-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Full day
        </h2>
        <div className="space-y-2">
          {todays.map((s) => (
            <SessionCard key={s.sessionId} session={s} bundle={bundle} compact />
          ))}
        </div>
      </section>
    </div>
  );
}
