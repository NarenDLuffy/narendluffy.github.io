import { Link } from "@tanstack/react-router";
import { Archive, CalendarClock, CircleAlert, WifiOff } from "lucide-react";
import type { Meeting } from "@/types/meeting";
import type { ScheduleBundle } from "@/types/schedule";
import { daysUntil } from "@/services/meetingService";
import { setSelectedMeetingId } from "@/services/meetingSelection";

/**
 * Meeting-state and ingestion-health banners.
 *
 * All copy is derived from the meeting registry and the ingest status written
 * by the pipeline; nothing here refers to a specific meeting.
 */
export function MeetingBanner({
  meeting,
  bundle,
  stale,
  isCurrent,
}: {
  meeting: Meeting;
  bundle: ScheduleBundle | null;
  stale: boolean;
  isCurrent: boolean;
}) {
  const banners = [] as { key: string; node: React.ReactNode }[];

  if (!isCurrent) {
    banners.push({
      key: "archive",
      node: (
        <Box tone="muted" icon={<Archive className="size-4" />} title={`Viewing ${meeting.name}`}>
          <button
            type="button"
            onClick={() => setSelectedMeetingId("")}
            className="underline underline-offset-2"
          >
            Switch back to the current meeting
          </button>
        </Box>
      ),
    });
  }

  if (meeting.status === "upcoming") {
    const days = daysUntil(meeting);
    banners.push({
      key: "upcoming",
      node: (
        <Box
          tone="muted"
          icon={<CalendarClock className="size-4" />}
          title={`${meeting.name} starts ${days <= 0 ? "today" : `in ${days} day${days === 1 ? "" : "s"}`}`}
        >
          {bundle?.sessions.length
            ? "Initial schedule available — you can build My agenda already."
            : "Schedule not yet published. It appears here automatically as soon as the first document is found."}
        </Box>
      ),
    });
  }

  if (bundle && bundle.ingest.state !== "ok") {
    banners.push({
      key: "ingest",
      node: (
        <Box tone="warn" icon={<CircleAlert className="size-4" />} title="Schedule update delayed">
          {`Last successful update ${new Date(bundle.ingest.lastSuccessfulAt).toLocaleTimeString()}. The previous verified schedule is still being shown.`}{" "}
          <Link to="/admin" className="underline underline-offset-2">
            Details
          </Link>
        </Box>
      ),
    });
  }

  if (stale) {
    banners.push({
      key: "stale",
      node: (
        <Box tone="warn" icon={<WifiOff className="size-4" />} title="Showing cached schedule">
          {bundle
            ? `Last successful download ${new Date(bundle.generatedAt).toLocaleTimeString()}.`
            : "No connection to the published schedule."}
        </Box>
      ),
    });
  }

  if (banners.length === 0) return null;
  return <div className="space-y-2">{banners.map((b) => <div key={b.key}>{b.node}</div>)}</div>;
}

function Box({
  tone,
  icon,
  title,
  children,
}: {
  tone: "muted" | "warn";
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={
        tone === "warn"
          ? "flex items-start gap-2 rounded-md border border-warn/40 bg-warn/10 p-3 text-sm"
          : "flex items-start gap-2 rounded-md border border-border bg-card p-3 text-sm"
      }
    >
      <span className={tone === "warn" ? "mt-0.5 text-warn" : "mt-0.5 text-muted-foreground"}>
        {icon}
      </span>
      <div>
        <div className="font-medium">{title}</div>
        <div className="text-xs text-muted-foreground">{children}</div>
      </div>
    </div>
  );
}
