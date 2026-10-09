import { Link } from "@tanstack/react-router";
import { useEffect, useRef } from "react";
import type { Room, Session } from "@/types/schedule";
import { minutesOf } from "@/services/scheduleService";
import { roomLabel, roomStyle } from "@/lib/rooms";
import { cn } from "@/lib/utils";

const PX_PER_MIN = 1.6;

export function Timetable({
  rooms,
  sessions,
  nowMinutes,
  showNowMarker,
  scrollToNowKey,
  isMatch,
  onSelect,
}: {
  rooms: Room[];
  sessions: Session[];
  nowMinutes: number;
  showNowMarker: boolean;
  scrollToNowKey?: number;
  /** When set, non-matching blocks are greyed out (agenda filter). */
  isMatch?: ((s: Session) => boolean) | undefined;
  onSelect?: ((s: Session) => void) | undefined;
}) {
  const scroller = useRef<HTMLDivElement>(null);

  // Every day spans the standard meeting window, extended only if a session
  // published by a chair falls outside it.
  const DAY_START = 8 * 60 + 30;
  const DAY_END = 19 * 60 + 30;
  const times = sessions.flatMap((s) => [minutesOf(s.startTime), minutesOf(s.endTime)]);
  const start = Math.min(DAY_START, ...times.map((t) => Math.floor(t / 30) * 30));
  const end = Math.max(DAY_END, ...times.map((t) => Math.ceil(t / 30) * 30));

  const height = (end - start) * PX_PER_MIN;

  const ticks: number[] = [];
  for (let t = start; t <= end; t += 30) ticks.push(t);

  useEffect(() => {
    if (!showNowMarker || !scroller.current) return;
    const y = (nowMinutes - start) * PX_PER_MIN - 120;
    scroller.current.scrollTo({ top: Math.max(0, y), behavior: "smooth" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scrollToNowKey]);

  // Breaks and lunches belong to the whole week grid, not to one room.
  const bands = sessions.filter((s) => !s.roomId && (s.kind === "break" || s.kind === "lunch"));
  const activeRooms = rooms.filter((r) => sessions.some((s) => s.roomId === r.roomId));


  // Parallel sessions inside one track share the track's column side by side.
  const layout = new Map<string, { sessions: Session[]; laneOf: Map<string, number>; lanes: number }>();
  for (const room of activeRooms) {
    const roomSessions = sessions
      .filter((s) => s.roomId === room.roomId)
      .sort((a, b) => minutesOf(a.startTime) - minutesOf(b.startTime));
    const laneEnd: number[] = [];
    const laneOf = new Map<string, number>();
    for (const s of roomSessions) {
      const from = minutesOf(s.startTime);
      let lane = laneEnd.findIndex((e) => e <= from);
      if (lane === -1) lane = laneEnd.push(from) - 1;
      laneEnd[lane] = minutesOf(s.endTime);
      laneOf.set(s.sessionId, lane);
    }
    layout.set(room.roomId, { sessions: roomSessions, laneOf, lanes: Math.max(1, laneEnd.length) });
  }
  const widthOf = (roomId: string) => 160 * (layout.get(roomId)?.lanes ?? 1);

  return (
    <div ref={scroller} className="max-h-[70vh] overflow-auto rounded-lg border border-border">
      <div className="min-w-max">
        <div className="sticky top-0 z-20 flex border-b border-border bg-card">
          <div className="w-12 shrink-0 border-r border-border" />
          {activeRooms.map((room) => (
            <Link
              key={room.roomId}
              to="/rooms/$roomId"
              params={{ roomId: room.roomId }}
              style={{ width: widthOf(room.roomId), ...roomStyle(room) }}
              className="shrink-0 border-r border-b-[3px] border-r-border border-b-[var(--room-color)] px-2 py-2 text-xs font-semibold leading-tight last:border-r-0 hover:bg-secondary"
            >
              {roomLabel(room)}
              {room.floor ? (
                <div className="text-[10px] font-normal text-muted-foreground">{room.floor}</div>
              ) : null}
            </Link>
          ))}
        </div>


        <div className="relative flex" style={{ height }}>
          <div className="w-12 shrink-0 border-r border-border">
            {ticks.map((t) => (
              <div
                key={t}
                className="mono-code absolute -translate-y-1/2 pl-1 text-[10px] text-muted-foreground"
                style={{ top: (t - start) * PX_PER_MIN }}
              >
                {String(Math.floor(t / 60)).padStart(2, "0")}:{String(t % 60).padStart(2, "0")}
              </div>
            ))}
          </div>

          {ticks.map((t) => (
            <div
              key={`line-${t}`}
              className={cn(
                "pointer-events-none absolute inset-x-0 border-t",
                t % 60 === 0 ? "border-border" : "border-border/40",
              )}
              style={{ top: (t - start) * PX_PER_MIN }}
            />
          ))}

          {bands.map((b) => (
            <div
              key={b.sessionId}
              className="pointer-events-none absolute inset-x-0 z-[5] flex items-center justify-center border-y border-dashed border-border bg-secondary/70"
              style={{
                top: (minutesOf(b.startTime) - start) * PX_PER_MIN,
                height: (minutesOf(b.endTime) - minutesOf(b.startTime)) * PX_PER_MIN,
              }}
            >
              <span className="mono-code text-[10px] uppercase tracking-wide text-muted-foreground">
                {b.topic} · {b.startTime}–{b.endTime}
              </span>
            </div>
          ))}



          {activeRooms.map((room) => {
            const entry = layout.get(room.roomId)!;
            const { sessions: roomSessions, laneOf, lanes: laneCount } = entry;
            return (
              <div
                key={room.roomId}
                className="relative shrink-0 border-r border-border last:border-r-0"
                style={{ width: widthOf(room.roomId) }}
              >

                {roomSessions.map((s) => {
                  const top = (minutesOf(s.startTime) - start) * PX_PER_MIN;
                  const h = (minutesOf(s.endTime) - minutesOf(s.startTime)) * PX_PER_MIN;
                  const isBreak = s.kind === "break" || s.kind === "lunch";
                  const lane = laneOf.get(s.sessionId) ?? 0;
                  const dimmed = !isBreak && isMatch ? !isMatch(s) : false;
                  return (
                    <button
                      type="button"
                      onClick={() => onSelect?.(s)}
                      aria-label={`${s.topic} ${s.startTime}-${s.endTime}`}
                      key={s.sessionId}
                      style={{
                        top,
                        height: Math.max(h - 2, 14),
                        left: `${(lane / laneCount) * 100}%`,
                        width: `${(1 / laneCount) * 100}%`,
                        ...roomStyle(room),
                      }}
                      className={cn(
                        "absolute overflow-hidden rounded-md border px-1.5 py-1 text-left transition-opacity",
                        isBreak
                          ? "border-dashed border-border bg-secondary/60"
                          : "border-border bg-[color-mix(in_oklab,var(--room-color)_10%,var(--card))] hover:ring-2 hover:ring-ring",
                        dimmed && "bg-card opacity-35 grayscale",
                        !dimmed && isMatch && !isBreak && "ring-2 ring-[var(--room-color)]",
                      )}
                    >
                      {!isBreak ? (
                        <span
                          className={cn(
                            "absolute inset-y-0 left-0 w-1",
                            dimmed ? "bg-border" : "bg-[var(--room-color)]",
                          )}
                          aria-hidden
                        />
                      ) : null}
                      <div
                        className={cn(
                          "flex items-baseline gap-1 text-[11px] font-semibold leading-tight",
                          !isBreak && "pl-1",
                        )}
                      >
                        {s.group ? (
                          <span className="mono-code shrink-0 rounded bg-secondary px-1 text-[9px] uppercase text-muted-foreground">
                            {s.group}
                          </span>
                        ) : null}
                        <span className="truncate">{s.topic}</span>
                      </div>
                      {(() => {
                        // An untimed block lists its items, with the chair's stated minutes.
                        const untimed = (s.agendaBreakdown ?? []).filter((b) => !b.startTime);
                        if (untimed.length > 1) {
                          return (
                            <div className="mono-code pl-1 text-[10px] text-muted-foreground">
                              {untimed
                                .map((b) => `${b.code ?? b.label}${b.minutes ? ` (${b.minutes})` : ""}`)
                                .join(" · ")}
                              {s.note?.includes("don't add up") ? (
                                <span className="ml-1 font-semibold text-destructive" title={s.note}>
                                  ⚠
                                </span>
                              ) : null}
                            </div>
                          );
                        }
                        return s.agendaItems.length > 0 ? (
                          <div className="mono-code pl-1 text-[10px] text-muted-foreground">
                            {s.agendaItems.join(" · ")}
                          </div>
                        ) : null;
                      })()}
                      <div className="mono-code pl-1 text-[10px] text-muted-foreground">
                        {s.startTime}-{s.endTime}
                        {s.sessionLead && h > 60 ? ` · ${s.sessionLead}` : ""}
                      </div>

                    </button>
                  );
                })}
              </div>
            );
          })}


          {showNowMarker && nowMinutes >= start && nowMinutes <= end ? (
            <div
              className="pointer-events-none absolute inset-x-0 z-10 border-t-2 border-live"
              style={{ top: (nowMinutes - start) * PX_PER_MIN }}
            >
              <span className="mono-code absolute -top-2 left-0 rounded bg-live px-1 text-[10px] font-bold text-background">
                now
              </span>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
