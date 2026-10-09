import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { BellPlus, Star, Trash2 } from "lucide-react";
import type { ScheduleBundle, Session } from "@/types/schedule";
import { agendaTitle, roomLabelById, roomStyle } from "@/lib/rooms";
import { useBookmarks } from "@/hooks/useBookmarks";
import { useDeadlines } from "@/hooks/useDeadlines";
import { cn } from "@/lib/utils";
import { RoomColleagues } from "@/components/RoomColleagues";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

export function SessionDetailSheet({
  bundle,
  session,
  onOpenChange,
}: {
  bundle: ScheduleBundle;
  session: Session | null;
  onOpenChange: (open: boolean) => void;
}) {
  const room = session ? bundle.rooms.find((r) => r.roomId === session.roomId) : undefined;
  const { isBookmarked, toggle } = useBookmarks();
  const { deadlines, add, remove } = useDeadlines(bundle.meeting.id);
  const [form, setForm] = useState<{ code: string; date: string; time: string; label: string }>();

  const breakdown = session?.agendaBreakdown ?? [];
  const codes = session
    ? [...new Set([...session.agendaItems, ...breakdown.flatMap((b) => (b.code ? [b.code] : []))])]
    : [];

  return (
    <Sheet open={Boolean(session)} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="max-h-[85vh] overflow-y-auto">
        {session ? (
          <>
            <SheetHeader className="text-left">
              <SheetTitle>{session.topic}</SheetTitle>
              <SheetDescription asChild>
                <div style={roomStyle(room)} className="flex flex-wrap items-center gap-2">
                  <span className="mono-code">
                    {session.day} {session.startTime}–{session.endTime}
                  </span>
                  {session.roomId ? (
                    <Link
                      to="/rooms/$roomId"
                      params={{ roomId: session.roomId }}
                      className="inline-flex items-center gap-1.5 font-medium text-foreground underline-offset-2 hover:underline"
                    >
                      <span className="size-2.5 rounded-full bg-[var(--room-color)]" aria-hidden />
                      {roomLabelById(bundle, session.roomId, session.roomName)}
                    </Link>
                  ) : null}
                  {session.sessionLead ? <span>Lead: {session.sessionLead}</span> : null}
                </div>
              </SheetDescription>
            </SheetHeader>

            <div className="mt-4 space-y-4 px-4 pb-6">
              {session.roomId ? (
                <RoomColleagues
                  meetingId={bundle.meeting.id}
                  roomId={session.roomId}
                  sessionId={session.sessionId}
                />
              ) : null}
              {breakdown.length > 0 ? (
                <section>
                  <h4 className="mb-1.5 text-xs font-semibold uppercase text-muted-foreground">
                    Time breakdown
                  </h4>
                  <ol className="space-y-1.5 text-sm">
                    {breakdown.map((slot, i) => (
                      <li key={`${slot.label}-${i}`} className="flex gap-2">
                        <span className="mono-code w-24 shrink-0 text-muted-foreground">
                          {slot.startTime && slot.endTime
                            ? `${slot.startTime}–${slot.endTime}`
                            : slot.minutes
                              ? `${slot.minutes} min`
                              : ""}
                        </span>
                        <span>
                          {slot.code ? <span className="mono-code mr-1 font-semibold">{slot.code}</span> : null}
                          {(slot.code && agendaTitle(bundle.agendaItems, slot.code)) ||
                            slot.label.replace(slot.code ?? "", "").trim()}
                        </span>
                      </li>
                    ))}
                  </ol>
                </section>
              ) : null}

              {codes.length > 0 ? (
                <section>
                  <h4 className="mb-1.5 text-xs font-semibold uppercase text-muted-foreground">
                    Agenda items
                  </h4>
                  <ul className="space-y-2">
                    {codes.map((code) => {
                      const mine = deadlines.filter((d) => d.code === code);
                      return (
                        <li key={code} className="rounded-md border border-border p-2.5">
                          <div className="flex items-start gap-2">
                            <button
                              type="button"
                              onClick={() => toggle(code)}
                              aria-label={isBookmarked(code) ? "Remove from my agenda" : "Add to my agenda"}
                              className={cn(
                                "mt-0.5 shrink-0",
                                isBookmarked(code) ? "text-primary" : "text-muted-foreground",
                              )}
                            >
                              <Star className={cn("size-4", isBookmarked(code) && "fill-current")} />
                            </button>
                            <div className="min-w-0 flex-1 text-sm">
                              <span className="mono-code mr-1.5 font-semibold">{code}</span>
                              {agendaTitle(bundle.agendaItems, code) ?? (
                                <span className="text-muted-foreground">Title not published</span>
                              )}
                            </div>
                            <button
                              type="button"
                              onClick={() =>
                                setForm({ code, date: session.date, time: "18:00", label: "FL summary" })
                              }
                              className="inline-flex shrink-0 items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                            >
                              <BellPlus className="size-3.5" /> Deadline
                            </button>
                          </div>
                          {mine.map((d) => (
                            <div
                              key={d.id}
                              className="mt-1.5 flex items-center gap-2 pl-6 text-xs text-warn"
                            >
                              <span>
                                {d.label} due {d.date} {d.time}
                              </span>
                              <button type="button" onClick={() => remove(d.id)} aria-label="Remove deadline">
                                <Trash2 className="size-3.5" />
                              </button>
                            </div>
                          ))}
                          {form?.code === code ? (
                            <form
                              className="mt-2 flex flex-wrap items-center gap-1.5 pl-6"
                              onSubmit={(e) => {
                                e.preventDefault();
                                if (form) add(form);
                                setForm(undefined);
                              }}
                            >
                              <input
                                value={form?.label ?? ""}
                                onChange={(e) => { const v = e.target.value; setForm((cur) => cur && { ...cur, label: v }); }}
                                className="min-h-9 w-32 rounded border border-input bg-card px-2 text-xs"
                                aria-label="Deadline name"
                              />
                              <input
                                type="date"
                                value={form?.date ?? ""}
                                onChange={(e) => { const v = e.target.value; setForm((cur) => cur && { ...cur, date: v }); }}
                                className="min-h-9 rounded border border-input bg-card px-2 text-xs"
                              />
                              <input
                                type="time"
                                value={form?.time ?? ""}
                                onChange={(e) => { const v = e.target.value; setForm((cur) => cur && { ...cur, time: v }); }}
                                className="min-h-9 rounded border border-input bg-card px-2 text-xs"
                              />
                              <button
                                type="submit"
                                className="min-h-9 rounded bg-primary px-2.5 text-xs font-semibold text-primary-foreground"
                              >
                                Save
                              </button>
                            </form>
                          ) : null}
                          <Link
                            to="/drafts/$code"
                            params={{ code }}
                            className="mt-1 block pl-6 text-xs text-muted-foreground underline-offset-2 hover:underline"
                          >
                            Drafts &amp; FL summaries
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Deadlines are in meeting time and are kept on this device. Export the timetable to
                    get a calendar reminder 30 minutes before.
                  </p>
                </section>
              ) : null}
              {session.note ? <p className="text-sm text-muted-foreground">{session.note}</p> : null}
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
