import { Link } from "@tanstack/react-router";
import { Info, Star, Flag } from "lucide-react";
import { useState } from "react";
import type { ScheduleBundle, Session } from "@/types/schedule";
import { sourceLabel } from "@/services/scheduleService";
import { useBookmarks } from "@/hooks/useBookmarks";
import { topicStyle } from "@/lib/topics";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

export function AgendaChip({
  code,
  onToggle,
  starred,
}: {
  code: string;
  onToggle?: (code: string) => void;
  starred?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onToggle ? () => onToggle(code) : undefined}
      className={cn(
        "mono-code inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-xs font-medium",
        starred
          ? "border-primary bg-primary/10 text-primary"
          : "border-border bg-secondary text-secondary-foreground",
      )}
    >
      {starred ? <Star className="size-3 fill-current" /> : null}
      {code}
    </button>
  );
}

export function SessionCard({
  session,
  bundle,
  live,
  compact,
}: {
  session: Session;
  bundle: ScheduleBundle;
  live?: boolean;
  compact?: boolean;
}) {
  const { isBookmarked, toggle } = useBookmarks();
  const [open, setOpen] = useState(false);

  return (
    <article
      style={topicStyle(session.topicKey)}
      className={cn(
        "relative overflow-hidden rounded-lg border bg-card pl-3",
        live ? "border-live/60 shadow-sm" : "border-border",
      )}
    >
      <span className="topic-bar absolute inset-y-0 left-0 w-1.5" aria-hidden />
      <div className="p-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="truncate text-base font-semibold leading-tight">{session.topic}</h3>
              {live ? (
                <span className="mono-code rounded bg-live/15 px-1.5 py-0.5 text-[10px] font-bold uppercase text-live">
                  live
                </span>
              ) : null}
              {session.status !== "scheduled" ? (
                <span className="mono-code rounded bg-warn/15 px-1.5 py-0.5 text-[10px] font-bold uppercase text-warn">
                  {session.status}
                </span>
              ) : null}
            </div>
            <Link
              to="/rooms/$roomId"
              params={{ roomId: session.roomId }}
              className="text-sm text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
            >
              {session.roomName}
            </Link>
          </div>
          <div className="mono-code shrink-0 text-right text-sm font-semibold tabular">
            <div>{session.startTime}</div>
            <div className="text-muted-foreground">{session.endTime}</div>
          </div>
        </div>

        {breakdown.length > 0 ? (
          <ol className="mt-2 space-y-1">
            {breakdown.map((slot, index) => (
              <li
                key={`${slot.label}-${index}`}
                className="flex items-baseline gap-2 text-xs leading-tight"
              >
                <span className="mono-code w-[76px] shrink-0 tabular text-muted-foreground">
                  {slot.startTime && slot.endTime
                    ? `${slot.startTime}-${slot.endTime}`
                    : slot.minutes
                      ? `${slot.minutes} min`
                      : ""}
                </span>
                <span className="min-w-0 flex-1 truncate">
                  {slot.code ? (
                    <button
                      type="button"
                      onClick={() => toggle(slot.code as string)}
                      className={cn(
                        "mono-code mr-1 font-medium underline-offset-2 hover:underline",
                        isBookmarked(slot.code) ? "text-primary" : "",
                      )}
                    >
                      {slot.code}
                    </button>
                  ) : null}
                  {slot.label !== slot.code ? slot.label.replace(slot.code ?? "", "").trim() : null}
                </span>
                {slot.minutes ? (
                  <span className="mono-code shrink-0 text-muted-foreground">{slot.minutes}m</span>
                ) : null}
              </li>
            ))}
          </ol>
        ) : session.agendaItems.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {session.agendaItems.map((code) => (
              <AgendaChip
                key={code}
                code={code}
                starred={isBookmarked(code)}
                onToggle={toggle}
              />
            ))}
          </div>
        ) : null}

        {!compact ? (
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            {session.sessionLead ? <span>Lead: {session.sessionLead}</span> : null}
            <span>{session.day}</span>
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger asChild>
                <button
                  type="button"
                  className="inline-flex items-center gap-1 underline-offset-2 hover:text-foreground hover:underline"
                >
                  <Info className="size-3.5" />
                  Sources
                </button>
              </DialogTrigger>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle>{session.topic}</DialogTitle>
                  <DialogDescription>
                    Automatically parsed from the meeting documents below.
                  </DialogDescription>
                </DialogHeader>
                <ul className="space-y-3 text-sm">
                  {session.sources.map((ref) => {
                    const src = bundle.sources.find((s) => s.sourceId === ref.sourceId);
                    return (
                      <li key={ref.sourceId} className="rounded-md border border-border p-2.5">
                        <div className="font-medium">{sourceLabel(bundle, ref.sourceId)}</div>
                        <div className="mono-code break-words text-xs text-muted-foreground">
                          {src?.fileName}
                        </div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          Contributed: {ref.contributed.join(", ")}
                        </div>
                      </li>
                    );
                  })}
                </ul>
                <button
                  type="button"
                  className="inline-flex items-center justify-center gap-1.5 rounded-md border border-border px-3 py-2 text-sm font-medium hover:bg-secondary"
                  onClick={() => setOpen(false)}
                >
                  <Flag className="size-3.5" />
                  Report issue (review queue)
                </button>
              </DialogContent>
            </Dialog>
          </div>
        ) : null}
      </div>
    </article>
  );
}
