import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Users } from "lucide-react";
import { useActiveMeeting } from "@/hooks/useActiveMeeting";
import { useCompanyPresence } from "@/hooks/useCompanyPresence";
import { useBookmarks } from "@/hooks/useBookmarks";
import { buildCoverage } from "@/services/presenceService";
import { MeetingBanner } from "@/components/MeetingBanner";
import { LoadingState, NoMeetingState } from "@/components/ScheduleStates";

export const Route = createFileRoute("/company")({
  head: () => ({
    meta: [
      { title: "My company — RAN1 Live" },
      {
        name: "description",
        content:
          "Coordinate RAN1 session coverage with colleagues using a shared company code. Voluntary room check-in, no accounts, never GPS.",
      },
      { property: "og:title", content: "My company — RAN1 Live" },
      {
        property: "og:description",
        content: "See which rooms colleagues are covering during the RAN1 meeting week.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: CompanyPage,
});

function CompanyPage() {
  const { meeting, bundle, stale, isCurrent, isLoading, clock } = useActiveMeeting();
  const { identity, joined, presence, join, leave } = useCompanyPresence(meeting?.id);
  const { bookmarks } = useBookmarks();
  const [code, setCode] = useState("");
  const [name, setName] = useState("");

  if (isLoading) return <LoadingState label="Loading company view…" />;
  if (!meeting) return <NoMeetingState />;

  const coverage = bundle
    ? buildCoverage(bundle, presence, bookmarks, clock.localDate, clock.nowMinutes)
    : [];

  const byRoom = new Map<string, typeof presence>();
  presence.forEach((p) => {
    const list = byRoom.get(p.roomId) ?? [];
    list.push(p);
    byRoom.set(p.roomId, list);
  });
  const roomName = (roomId: string) =>
    bundle?.rooms.find((r) => r.roomId === roomId)?.roomName ?? roomId;

  return (
    <div className="space-y-5">
      <MeetingBanner meeting={meeting} bundle={bundle} stale={stale} isCurrent={isCurrent} />

      <header className="space-y-1">
        <h1 className="text-lg font-semibold">My company</h1>
        <p className="text-xs text-muted-foreground">
          No accounts. Everyone from your company types the same code; presence is shown only to
          people who know it, and only for {meeting.name}.
        </p>
      </header>

      {!joined ? (
        <form
          className="space-y-2 rounded-lg border border-border bg-card p-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (code.trim()) join(code, name.trim());
          }}
        >
          <label className="block text-xs font-medium">
            Company code
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="e.g. acme-ran1"
              className="mono-code mt-1 min-h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
          </label>
          <label className="block text-xs font-medium">
            Your name (shown to colleagues)
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="optional"
              className="mt-1 min-h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
          </label>
          <button
            type="submit"
            className="min-h-11 w-full rounded-md bg-primary text-sm font-semibold text-primary-foreground"
          >
            Join company group
          </button>
        </form>
      ) : (
        <div className="flex items-center gap-3 rounded-lg border border-border bg-card p-3 text-sm">
          <Users className="size-4 text-primary" />
          <div className="min-w-0 flex-1">
            <div className="mono-code truncate font-medium">{identity.groupId}</div>
            <div className="truncate text-xs text-muted-foreground">
              {identity.displayName || "anonymous"} · {presence.length} checked in
            </div>
          </div>
          <button
            type="button"
            onClick={() => void leave()}
            className="min-h-10 rounded-md border border-border px-3 text-xs font-medium"
          >
            Leave
          </button>
        </div>
      )}

      {joined ? (
        <>
          <section className="space-y-2">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Colleagues by room
            </h2>
            {byRoom.size === 0 ? (
              <p className="rounded-lg border border-dashed border-border p-3 text-xs text-muted-foreground">
                Nobody is checked in. Open a{" "}
                <Link to="/rooms" className="underline underline-offset-2">
                  room
                </Link>{" "}
                and tap “I'm in this room”.
              </p>
            ) : (
              <ul className="space-y-2">
                {[...byRoom.entries()].map(([roomId, people]) => (
                  <li key={roomId} className="rounded-lg border border-border bg-card p-3">
                    <Link
                      to="/rooms/$roomId"
                      params={{ roomId }}
                      className="text-sm font-medium underline-offset-2 hover:underline"
                    >
                      {roomName(roomId)}
                    </Link>
                    <p className="text-xs text-muted-foreground">
                      {people.map((p) => p.displayName || "Colleague").join(", ")}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="space-y-2">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Coverage right now
            </h2>
            {coverage.length === 0 ? (
              <p className="rounded-lg border border-dashed border-border p-3 text-xs text-muted-foreground">
                No parallel sessions running at the moment.
              </p>
            ) : (
              <ul className="space-y-2">
                {coverage.map((row) => (
                  <li
                    key={row.sessionId}
                    className="flex items-center gap-3 rounded-lg border border-border bg-card p-3"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium">{row.topic}</span>
                      <span className="mono-code block truncate text-xs text-muted-foreground">
                        {row.roomName} · {row.startTime}–{row.endTime}
                        {row.agendaItems.length ? ` · ${row.agendaItems.join(", ")}` : ""}
                      </span>
                    </span>
                    <span
                      className={
                        row.colleaguesPresent === 0
                          ? "mono-code rounded bg-warn/15 px-2 py-1 text-xs font-bold text-warn"
                          : "mono-code rounded bg-live/15 px-2 py-1 text-xs font-bold text-live"
                      }
                    >
                      {row.colleaguesPresent}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}

      <p className="rounded-lg border border-dashed border-border p-3 text-xs text-muted-foreground">
        Presence is voluntary, expires automatically and never uses location. Anyone with your
        company code can see and post presence, so share it only inside your company.
      </p>
    </div>
  );
}
