import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Lock, MapPin } from "lucide-react";
import { scheduleQueryOptions, minutesOf } from "@/services/schedule";
import { useMeetingClock } from "@/hooks/useMeetingClock";
import { SessionCard } from "@/components/SessionCard";

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
    ],
  }),
  component: RoomPage,
});

function RoomPage() {
  const { roomId } = Route.useParams();
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

  const room = bundle.rooms.find((r) => r.roomId === roomId);
  if (!room) {
    return (
      <div className="py-10 text-center text-sm text-muted-foreground">
        Unknown room. <Link to="/rooms" className="underline">Back to rooms</Link>
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

  return (
    <div className="space-y-5">
      <Link to="/rooms" className="inline-flex items-center gap-1 text-sm text-muted-foreground">
        <ArrowLeft className="size-4" /> Rooms
      </Link>

      <header>
        <h1 className="text-xl font-semibold">{room.roomName}</h1>
        <p className="flex items-center gap-1 text-xs text-muted-foreground">
          <MapPin className="size-3.5" />
          {room.area ? `${room.area} · ` : ""}
          {bundle.meeting.venue}
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

      <section className="flex items-start gap-2 rounded-lg border border-border bg-secondary/50 p-3 text-sm">
        <Lock className="mt-0.5 size-4 text-muted-foreground" />
        <div>
          <div className="font-medium">Colleague presence</div>
          <p className="text-xs text-muted-foreground">
            Checking into a room and seeing colleagues arrives with verified company sign-in. No
            GPS is ever used, and presence stays inside your own company.
          </p>
        </div>
      </section>

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
