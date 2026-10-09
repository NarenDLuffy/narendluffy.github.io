import { Link } from "@tanstack/react-router";
import { BellRing, X } from "lucide-react";
import { useCompanyAlerts } from "@/hooks/useCompanyAlerts";

function hhmm(iso: string, timeZone?: string) {
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    ...(timeZone ? { timeZone } : {}),
  }).format(new Date(iso));
}

/** Big overlay listing every active "colleague needed" alert for the company. */
export function CompanyAlertBanner({
  meetingId,
  timeZone,
}: {
  meetingId: string | undefined;
  timeZone?: string | undefined;
}) {
  const { alerts, dismiss, cancel, myUserId } = useCompanyAlerts(meetingId);
  if (alerts.length === 0) return null;

  return (
    <div className="pointer-events-none fixed inset-x-0 top-0 z-50 flex justify-center p-3">
      <div
        role="alert"
        className="pointer-events-auto w-full max-w-2xl rounded-xl border-2 border-warn bg-card p-4 shadow-2xl"
      >
        <div className="mb-2 flex items-center gap-2">
          <BellRing className="size-6 animate-pulse text-warn" />
          <h2 className="flex-1 text-lg font-bold">
            {alerts.length === 1 ? "Colleague needed" : `Colleagues needed (${alerts.length})`}
          </h2>
          <button
            type="button"
            onClick={() => dismiss(alerts.map((a) => a.id))}
            className="min-h-10 rounded-md border border-border px-3 text-xs font-medium"
          >
            {alerts.length > 1 ? "Close all" : "Close"}
          </button>
        </div>
        <ul className="space-y-2">
          {alerts.map((a) => (
            <li key={a.id} className="flex items-start gap-2 rounded-lg bg-secondary p-3">
              <p className="min-w-0 flex-1 text-base leading-snug">
                <strong>{a.targetName}</strong> is needed in{" "}
                <Link
                  to="/rooms/$roomId"
                  params={{ roomId: a.roomId }}
                  className="font-semibold underline underline-offset-2"
                >
                  {a.roomLabel || a.roomId}
                </Link>{" "}
                <span className="mono-code text-sm text-muted-foreground">
                  · {hhmm(a.createdAt, timeZone)}
                  {a.senderName ? ` · from ${a.senderName}` : ""}
                </span>
              </p>
              {a.senderId === myUserId ? (
                <button
                  type="button"
                  onClick={() => void cancel(a.id)}
                  className="min-h-9 shrink-0 rounded-md border border-border px-2 text-xs"
                >
                  Withdraw
                </button>
              ) : null}
              <button
                type="button"
                aria-label="Close this alert"
                onClick={() => dismiss([a.id])}
                className="flex size-9 shrink-0 items-center justify-center rounded-md hover:bg-background"
              >
                <X className="size-4" />
              </button>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-[11px] text-muted-foreground">
          Closing hides it only on this device. Alerts disappear for everyone after 10 minutes.
        </p>
      </div>
    </div>
  );
}
