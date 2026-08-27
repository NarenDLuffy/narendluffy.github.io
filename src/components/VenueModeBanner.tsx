import { useEffect, useState } from "react";
import { AlertTriangle, Radio, ShieldCheck, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  alwaysSwitch,
  autoHopToVenue,
  disableAlwaysSwitch,
  dismissVenueBanner,
  inVenueMode,
  secureModeUrl,
  setAlwaysSwitch,
  switchToVenueMode,
  venueBannerDismissed,
  venueBlockedByScheme,
  venueHopFailed,
  venueModeUrl,
  venueTwinLoadedOverHttps,
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
  const [state, setState] = useState<"hidden" | "offer" | "in-venue" | "blocked" | "https-twin">(
    "hidden",
  );
  const [always, setAlways] = useState(false);

  useEffect(() => {
    setAlways(alwaysSwitch());
    if (inVenueMode()) {
      setState("in-venue");
      return undefined;
    }
    if (venueTwinLoadedOverHttps()) {
      setState("https-twin");
      return undefined;
    }
    if (!venueBlockedByScheme() || !meetingActive) return undefined;
    // A twin that the browser already force-upgraded to HTTPS (HSTS), or no
    // twin configured at all: explain instead of offering a broken switch.
    if (venueHopFailed() || !VENUE_HOST) {
      if (!venueBannerDismissed()) setState("blocked");
      return undefined;
    }
    if (alwaysSwitch()) {
      // Redirect immediately; the component unmounts before it can paint.
      autoHopToVenue();
      return undefined;
    }
    if (!venueBannerDismissed()) setState("offer");
    return undefined;
  }, [meetingActive]);

  if (state === "hidden") return null;

  if (state === "in-venue") {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-primary/40 bg-primary/5 p-3 text-xs">
        <Radio className="mt-0.5 size-4 shrink-0 text-primary" />
        <div className="min-w-0 flex-1 space-y-2 text-muted-foreground">
          <p>
            <span className="font-medium text-foreground">Venue mode.</span> This copy is served
            over plain HTTP so it can read the meeting-room server directly. Check-ins and anything
            account-based live on the secure site.{" "}
            <a className="font-medium text-primary underline" href={secureModeUrl(secureHost)}>
              Back to {secureHost}
            </a>
          </p>
          <label className="flex items-center gap-2 text-foreground">
            <input
              type="checkbox"
              checked={always}
              onChange={(e) => {
                setAlways(e.target.checked);
                setAlwaysSwitch(e.target.checked);
              }}
              className="size-3.5 accent-[hsl(var(--primary))]"
            />
            Always open venue mode at meetings
          </label>
        </div>
      </div>
    );
  }

  if (state === "https-twin") {
    return (
      <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-xs">
        <div className="flex items-start gap-2">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
          <div className="min-w-0 flex-1 space-y-2 text-muted-foreground">
            <p>
              <span className="font-medium text-foreground">Venue mode opened over HTTPS.</span>{" "}
              This browser upgraded {VENUE_HOST} to HTTPS. GitHub Pages supports that secure
              connection, so this page cannot read the meeting-room server at 10.10.10.10.
            </p>
            <p>
              Schedule and drafts remain available from the public meeting sync. Venue-only
              updates may arrive a few minutes later.
            </p>

            <div className="flex flex-wrap items-center gap-2">
              <Button asChild size="sm" variant="outline">
                <a href={secureModeUrl(secureHost)}>Back to {secureHost}</a>
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  disableAlwaysSwitch();
                  setAlways(false);
                }}
              >
                Stop auto-opening venue mode
              </Button>
            </div>
          </div>
        </div>
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
            ? "Your browser upgraded the venue copy to HTTPS, which cannot read the meeting-room server. Schedule and drafts will continue through the public meeting sync."
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
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => switchToVenueMode(false)}
            className="inline-flex min-h-9 items-center rounded-md border border-primary bg-primary/10 px-2.5 text-xs font-medium text-primary"
          >
            Open venue mode
          </button>
          <label className="inline-flex items-center gap-2 text-foreground">
            <input
              type="checkbox"
              checked={always}
              onChange={(e) => {
                const checked = e.target.checked;
                setAlways(checked);
                setAlwaysSwitch(checked);
                if (checked) switchToVenueMode(true);
              }}
              className="size-3.5 accent-[hsl(var(--primary))]"
            />
            Always open venue mode
          </label>
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
