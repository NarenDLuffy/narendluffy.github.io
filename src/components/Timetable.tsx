import { Link } from "@tanstack/react-router";
import { useEffect, useRef } from "react";
import type { Room, Session } from "@/types/schedule";
import { minutesOf } from "@/services/scheduleService";
import { topicStyle } from "@/lib/topics";
import { cn } from "@/lib/utils";

const PX_PER_MIN = 1.6;

export function Timetable({
  rooms,
  sessions,
  nowMinutes,
  showNowMarker,
  scrollToNowKey,
}: {
  rooms: Room[];
  sessions: Session[];
  nowMinutes: number;
  showNowMarker: boolean;
  scrollToNowKey?: number;
}) {
  const scroller = useRef<HTMLDivElement>(null);

  const times = sessions.flatMap((s) => [minutesOf(s.startTime), minutesOf(s.endTime)]);
  const start = times.length ? Math.floor(Math.min(...times) / 30) * 30 : 8 * 60;
  const end = times.length ? Math.ceil(Math.max(...times) / 30) * 30 : 18 * 60;
  const height = (end - start) * PX_PER_MIN;

  const ticks: number[] = [];
  for (let t = start; t <= end; t += 30) ticks.push(t);

  useEffect(() => {
    if (!showNowMarker || !scroller.current) return;
    const y = (nowMinutes - start) * PX_PER_MIN - 120;
    scroller.current.scrollTo({ top: Math.max(0, y), behavior: "smooth" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scrollToNowKey]);

  const activeRooms = rooms.filter((r) => sessions.some((s) => s.roomId === r.roomId));

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
              className="w-40 shrink-0 border-r border-border px-2 py-2 text-xs font-semibold leading-tight last:border-r-0 hover:bg-secondary"
            >
              {room.roomName}
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

          {activeRooms.map((room) => (
            <div key={room.roomId} className="relative w-40 shrink-0 border-r border-border last:border-r-0">
              {sessions
                .filter((s) => s.roomId === room.roomId)
                .map((s) => {
                  const top = (minutesOf(s.startTime) - start) * PX_PER_MIN;
                  const h = (minutesOf(s.endTime) - minutesOf(s.startTime)) * PX_PER_MIN;
                  const isBreak = s.kind === "break" || s.kind === "lunch";
                  return (
                    <div
                      key={s.sessionId}
                      style={{ top, height: h - 2, ...topicStyle(s.topicKey) }}
                      className={cn(
                        "absolute inset-x-1 overflow-hidden rounded-md border px-1.5 py-1",
                        isBreak
                          ? "border-dashed border-border bg-secondary/60"
                          : "border-border bg-card",
                      )}
                    >
                      {!isBreak ? (
                        <span className="topic-bar absolute inset-y-0 left-0 w-1" aria-hidden />
                      ) : null}
                      <div className={cn("text-[11px] font-semibold leading-tight", !isBreak && "pl-1")}>
                        {s.topic}
                      </div>
                      {s.agendaItems.length > 0 ? (
                        <div className="mono-code pl-1 text-[10px] text-muted-foreground">
                          {s.agendaItems.join(" · ")}
                        </div>
                      ) : null}
                      <div className="mono-code pl-1 text-[10px] text-muted-foreground">
                        {s.startTime}-{s.endTime}
                        {s.sessionLead && h > 60 ? ` · ${s.sessionLead}` : ""}
                      </div>
                    </div>
                  );
                })}
            </div>
          ))}

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
