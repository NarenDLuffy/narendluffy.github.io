import { useEffect, useState } from "react";
import { AlertTriangle, Radio, ShieldCheck, X } from "lucide-react";
import {
  alwaysSwitch,
  dismissVenueBanner,
  inVenueMode,
  secureModeUrl,
  setAlwaysSwitch,
  switchToVenueMode,
  venueBannerDismissed,
  venueBlockedByScheme,
  venueHopFailed,
  VENUE_HOST,
} from "@/lib/venueMode";

/**
 * Venue mode switch.
 *
 * The meeting-room server at http://10.10.10.10 can only be read by a browser
 * that is (a) on the meeting Wi-Fi and (b) running a plain-HTTP page. This
 * banner is the one-tap bridge to that HTTP twin, and the way back afterwards.
 * Rendered client-side only: the decision depends on window.location.
 */
export function VenueModeBanner({
  meetingActive,
  secureHost = "ran1.app",
}: {
  meetingActive: boolean;
  secureHost?: string;
}) {
  const [state, setState] = useState<"hidden" | "offer" | "in-venue" | "blocked">("hidden");

  useEffect(() => {
    if (inVenueMode()) {
      setState("in-venue");
      return;
    }
    if (!venueBlockedByScheme() || !meetingActive) return;
    // A twin that the browser already force-upgraded to HTTPS (HSTS), or no
    // twin configured at all: explain instead of offering a broken switch.
    if (venueHopFailed() || !VENUE_HOST) {
      if (!venueBannerDismissed()) setState("blocked");
      return;
    }
    if (alwaysSwitch()) {
      switchToVenueMode();
      return;
    }
    if (!venueBannerDismissed()) setState("offer");
  }, [meetingActive]);

  if (state === "hidden") return null;

  if (state === "in-venue") {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-primary/40 bg-primary/5 p-3 text-xs">
        <Radio className="mt-0.5 size-4 shrink-0 text-primary" />
        <p className="min-w-0 flex-1 text-muted-foreground">
          <span className="font-medium text-foreground">Venue mode.</span> This copy is served over
          plain HTTP so it can read the meeting-room server directly. Check-ins and anything
          account-based live on the secure site.{" "}
          <a className="font-medium text-primary underline" href={secureModeUrl(secureHost)}>
            Back to {secureHost}
          </a>
        </p>
      </div>
    );
  }

  if (state === "blocked") {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-border bg-card p-3 text-xs">
        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        <p className="min-w-0 flex-1 text-muted-foreground">
          <span className="font-medium text-foreground">Venue mode unavailable.</span>{" "}
          {VENUE_HOST
            ? "Your browser forced the venue copy of this app to HTTPS, which cannot read the meeting-room server. This happens when the venue host sits under a domain with strict HTTPS (HSTS) — the venue twin must run on its own separate domain."
            : "The plain-HTTP venue copy of this app is not configured for this deployment yet. Drafts will fall back to the public 3GPP SYNC mirror, which may be a few minutes behind."}
        </p>
        <button
          type="button"
          aria-label="Dismiss"
          onClick={() => {
            dismissVenueBanner();
            setState("hidden");
          }}
          className="shrink-0 text-muted-foreground"
        >
          <X className="size-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2 rounded-lg border border-border bg-card p-3 text-xs">
      <ShieldCheck className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1 space-y-2">
        <p className="text-muted-foreground">
          <span className="font-medium text-foreground">At the meeting?</span> This secure page
          cannot read the venue server at 10.10.10.10 — browsers block HTTP content on an HTTPS
          page. Venue mode opens the same app on {VENUE_HOST} over plain HTTP, which can.
        </p>
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => switchToVenueMode(false)}
            className="inline-flex min-h-9 items-center rounded-md border border-primary bg-primary/10 px-2.5 text-xs font-medium text-primary"
          >
            Open venue mode
          </button>
          <button
            type="button"
            onClick={() => {
              setAlwaysSwitch(true);
              switchToVenueMode(true);
            }}
            className="inline-flex min-h-9 items-center rounded-md border border-border px-2.5 text-xs font-medium text-muted-foreground"
          >
            Always at venues
          </button>
        </div>
      </div>
      <button
        type="button"
        aria-label="Dismiss"
        onClick={() => {
          dismissVenueBanner();
          setState("hidden");
        }}
        className="shrink-0 text-muted-foreground"
      >
        <X className="size-4" />
      </button>
    </div>
  );
}
