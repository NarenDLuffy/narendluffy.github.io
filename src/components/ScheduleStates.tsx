import { Link } from "@tanstack/react-router";
import type { Meeting } from "@/types/meeting";
import { daysUntil, formatDateRange } from "@/services/meetingService";

export function LoadingState({ label = "Loading schedule…" }: { label?: string }) {
  return <p className="py-10 text-center text-sm text-muted-foreground">{label}</p>;
}

export function NoMeetingState() {
  return (
    <div className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
      <p className="font-medium text-foreground">No meetings discovered yet</p>
      <p className="mt-1 text-xs">
        Meetings appear automatically as soon as the ingestion pipeline finds a RAN1 folder on the
        3GPP server.
      </p>
    </div>
  );
}

/** Shown when a meeting exists but its schedule has not been published yet. */
export function NoScheduleState({ meeting }: { meeting: Meeting }) {
  const days = daysUntil(meeting);
  return (
    <div className="rounded-lg border border-dashed border-border p-6 text-center text-sm">
      <p className="font-medium">{meeting.name}</p>
      <p className="mono-code mt-0.5 text-xs text-muted-foreground">
        {formatDateRange(meeting.startDate, meeting.endDate)}
        {meeting.city ? ` · ${meeting.city}` : ""}
      </p>
      <p className="mt-3 text-xs text-muted-foreground">
        {meeting.status === "upcoming"
          ? `No schedule document published yet${days > 0 ? ` — the meeting starts in ${days} day${days === 1 ? "" : "s"}` : ""}. This page fills itself in automatically.`
          : "No schedule document could be parsed for this meeting."}
      </p>
      <Link
        to="/meetings"
        className="mt-3 inline-flex min-h-10 items-center rounded-md border border-border px-3 text-xs font-medium"
      >
        Browse meetings
      </Link>
    </div>
  );
}
