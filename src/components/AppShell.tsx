import { Link, useRouterState } from "@tanstack/react-router";
import { Clock, CalendarDays, Star, Building2, DoorOpen, GitCompareArrows } from "lucide-react";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { scheduleQueryOptions } from "@/services/schedule";
import { useMeetingClock } from "@/hooks/useMeetingClock";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Now", icon: Clock },
  { to: "/schedule", label: "Schedule", icon: CalendarDays },
  { to: "/agenda", label: "My agenda", icon: Star },
  { to: "/rooms", label: "Rooms", icon: DoorOpen },
  { to: "/company", label: "Company", icon: Building2 },
] as const;

function formatRange(startDate: string, endDate: string) {
  const s = new Date(`${startDate}T00:00:00Z`);
  const e = new Date(`${endDate}T00:00:00Z`);
  const day = (d: Date) => d.getUTCDate();
  const month = new Intl.DateTimeFormat("en-GB", { month: "long", timeZone: "UTC" }).format(e);
  return `${day(s)}-${day(e)} ${month} ${e.getUTCFullYear()}`;
}

export function AppShell({ children }: { children: ReactNode }) {
  const { data } = useQuery(scheduleQueryOptions);
  const pathname = useRouterState({ select: (s) => s.location.pathname });
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

  const updatedAt = bundle
    ? new Intl.DateTimeFormat("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: bundle.meeting.timezone,
      }).format(new Date(bundle.generatedAt))
    : "--:--";

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-30 border-b border-border bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2.5">
          <Link to="/" className="min-w-0 flex-1">
            <div className="flex items-baseline gap-2">
              <span className="mono-code text-base font-semibold tracking-tight">
                {bundle?.meeting.meetingName ?? "RAN1 Live"}
              </span>
              <span className="truncate text-xs text-muted-foreground">
                {bundle
                  ? `${bundle.meeting.city} · ${formatRange(bundle.meeting.startDate, bundle.meeting.endDate)}`
                  : "loading schedule"}
              </span>
            </div>
            <div className="mono-code text-[11px] text-muted-foreground">
              Updated {updatedAt}
              {data?.stale ? " · cached copy" : ""}
            </div>
          </Link>

          <nav className="hidden items-center gap-1 md:flex">
            {NAV.map((n) => (
              <Link
                key={n.to}
                to={n.to}
                className={cn(
                  "rounded-md px-2.5 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground",
                  pathname === n.to && "bg-secondary text-foreground",
                )}
              >
                {n.label}
              </Link>
            ))}
            <Link
              to="/changes"
              className={cn(
                "rounded-md px-2.5 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground",
                pathname === "/changes" && "bg-secondary text-foreground",
              )}
            >
              Changes
            </Link>
          </nav>

          <div className="mono-code shrink-0 rounded-md bg-secondary px-2 py-1 text-sm font-semibold tabular">
            {clock.localTime || "--:--"}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pb-28 pt-3 md:pb-12">{children}</main>

      <p className="mx-auto max-w-6xl px-4 pb-28 text-[11px] leading-snug text-muted-foreground md:pb-8">
        Unofficial RAN1 meeting companion. Schedule information is automatically generated from
        meeting documents and may contain errors.
      </p>

      <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-background/95 backdrop-blur md:hidden">
        <div className="flex">
          {NAV.map((n) => {
            const Icon = n.icon;
            const active = pathname === n.to;
            return (
              <Link
                key={n.to}
                to={n.to}
                className={cn(
                  "flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 py-2 text-[10px] font-medium uppercase tracking-wide",
                  active ? "text-primary" : "text-muted-foreground",
                )}
              >
                <Icon className="size-5" strokeWidth={active ? 2.4 : 1.8} />
                {n.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}

export function ChangesLink() {
  return (
    <Link
      to="/changes"
      className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-secondary hover:text-foreground"
    >
      <GitCompareArrows className="size-3.5" />
      Schedule changes
    </Link>
  );
}
