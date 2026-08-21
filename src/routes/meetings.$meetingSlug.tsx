import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import { useActiveMeeting } from "@/hooks/useActiveMeeting";
import { formatDateRange } from "@/services/meetingService";
import { setSelectedMeetingId } from "@/services/meetingSelection";
import { LoadingState } from "@/components/ScheduleStates";

export const Route = createFileRoute("/meetings/$meetingSlug")({
  head: () => ({
    meta: [
      { title: "Meeting details — RAN1 Live" },
      {
        name: "description",
        content:
          "Dates, venue, discovered documents and schedule coverage for a single 3GPP RAN1 meeting week.",
      },
      { property: "og:title", content: "RAN1 meeting details — RAN1 Live" },
      {
        property: "og:description",
        content: "Dates, venue and discovered schedule documents for one RAN1 meeting.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: MeetingDetailPage,
});

function MeetingDetailPage() {
  const { meetingSlug } = Route.useParams();
  const { meeting, bundle, isLoading } = useActiveMeeting(meetingSlug);
  const navigate = useNavigate();

  if (isLoading) return <LoadingState label="Loading meeting…" />;
  if (!meeting || meeting.slug !== meetingSlug) {
    return (
      <div className="py-10 text-center text-sm text-muted-foreground">
        Unknown meeting.{" "}
        <Link to="/meetings" className="underline">
          All meetings
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <Link to="/meetings" className="inline-flex items-center gap-1 text-sm text-muted-foreground">
        <ArrowLeft className="size-4" /> Meetings
      </Link>

      <header className="space-y-1">
        <h1 className="text-xl font-semibold">{meeting.name}</h1>
        <p className="mono-code text-xs text-muted-foreground">
          {formatDateRange(meeting.startDate, meeting.endDate)}
          {meeting.city ? ` · ${meeting.city}` : ""}
          {meeting.venue ? ` · ${meeting.venue}` : ""} · {meeting.timezone}
        </p>
      </header>

      <dl className="grid grid-cols-2 gap-2 text-sm">
        <Stat label="Status" value={meeting.status} />
        <Stat label="Sessions" value={String(bundle?.sessions.length ?? 0)} />
        <Stat label="Rooms" value={String(bundle?.rooms.length ?? 0)} />
        <Stat label="Documents" value={String(bundle?.sources.length ?? 0)} />
      </dl>

      {bundle?.sources.length ? (
        <section className="space-y-1">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Discovered documents
          </h2>
          <ul className="space-y-1">
            {bundle.sources.map((s) => (
              <li key={s.sourceId} className="mono-code text-[11px] text-muted-foreground">
                <span className="text-foreground">{s.label}</span> · {s.fileName}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <button
        type="button"
        onClick={() => {
          setSelectedMeetingId(meeting.id);
          navigate({ to: "/" });
        }}
        className="min-h-12 w-full rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground"
      >
        Open this meeting
      </button>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mono-code text-sm font-semibold capitalize">{value}</dd>
    </div>
  );
}
