import { Link } from "@tanstack/react-router";
import { Users } from "lucide-react";
import { useCompanyPresence } from "@/hooks/useCompanyPresence";

/** Colleagues checked into one room, with check-in / check-out. */
export function RoomColleagues({
  meetingId,
  roomId,
  sessionId,
}: {
  meetingId: string;
  roomId: string;
  sessionId?: string | undefined;
}) {
  const { joined, presence, myRoomId, enter, exit, shared, lastError } =
    useCompanyPresence(meetingId);
  const here = presence.filter((p) => p.roomId === roomId);
  const iAmHere = myRoomId === roomId;

  return (
    <section className="space-y-2 rounded-lg border border-border bg-card p-3">
      <div className="flex items-center gap-2">
        <Users className="size-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold">Colleagues in this room</h2>
        <span className="mono-code ml-auto text-xs text-muted-foreground">{here.length}</span>
      </div>
      {!joined ? (
        <p className="text-xs text-muted-foreground">
          Join your company group on the{" "}
          <Link to="/company" className="underline underline-offset-2">
            Company page
          </Link>{" "}
          to check in. No account required.
        </p>
      ) : (
        <>
          <ul className="flex flex-wrap gap-1.5">
            {here.length === 0 ? (
              <li className="text-xs text-muted-foreground">Nobody checked in here.</li>
            ) : (
              here.map((p) => (
                <li key={p.userId} className="rounded-md border border-border px-2 py-1 text-xs">
                  {p.displayName || "Colleague"}
                </li>
              ))
            )}
          </ul>
          <button
            type="button"
            onClick={() => (iAmHere ? void exit() : void enter(roomId, sessionId))}
            className={
              iAmHere
                ? "min-h-11 w-full rounded-md border border-border text-sm font-medium"
                : "min-h-11 w-full rounded-md bg-primary text-sm font-semibold text-primary-foreground"
            }
          >
            {iAmHere ? "Check out" : "I'm in this room"}
          </button>
          <PresenceStatus shared={shared} lastError={lastError} />
        </>
      )}
    </section>
  );
}

export function PresenceStatus({ shared, lastError }: { shared: boolean; lastError: string | null }) {
  return shared ? (
    <p className="text-[11px] text-muted-foreground">
      Shared with your company. Expires by itself; no GPS, no history.
    </p>
  ) : (
    <p className="text-[11px] font-medium text-warn">
      Can't reach the shared list — {reasonOf(lastError)} Check-ins are only on this device
      for now. Retrying…
    </p>
  );
}

function reasonOf(err: string | null): string {
  if (typeof console !== "undefined" && err) console.warn("[presence]", err);
  const e = (err ?? "").toLowerCase();
  if (typeof navigator !== "undefined" && !navigator.onLine) return "no internet connection.";
  if (e.includes("environment variable") || e.includes("jwt") || e.includes("api key"))
    return "the site's server isn't connected to the backend.";
  if (e.includes("fetch") || e.includes("network")) return "the server didn't answer.";
  return "the server returned an error.";
}
