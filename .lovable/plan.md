# Make venue mode actually automatic

## What you're seeing

The "Open venue mode" banner appears because the automatic hop can never succeed as
currently written, for two reasons:

1. **The toggle probably was never switched on.** The offer banner has two buttons
   ("Open venue mode" and "Always open venue mode") but no visible state showing whether
   auto-hop is already enabled. Only the in-venue banner has the checkbox. If you only ever
   tapped "Open venue mode", the preference was never stored, so every visit shows the offer.
2. **Even with the toggle on, the reachability probe always fails.** Before hopping, the app
   fetches `http://3gpplive.net/favicon.png` from the HTTPS page. Browsers block *any*
   HTTP subresource request from an HTTPS page (mixed content) — including `no-cors` fetches —
   so the probe rejects every time, auto-hop returns false, and the code falls back to the
   offer banner. This is the same restriction that forces venue mode to exist at all.

## Fix

- **Remove the probe from the auto-hop path.** A top-level navigation from HTTPS to HTTP is
  allowed (that's what the button already does); only subresource fetches are blocked. So when
  the toggle is on, a meeting is active, and the hop isn't marked failed, redirect immediately
  with `window.location.replace(venueModeUrl())` — no probe, no banner flash.
- **Keep the safety net.** The existing failed-hop marker still applies: if the browser
  upgrades the hop to HTTPS, the twin page marks the device as failed, auto-hop stops, and the
  "Venue mode unavailable" banner explains why. Add a guard so the twin, when it can't reach
  `10.10.10.10`, offers a one-tap return to `ran1.app` and clears the toggle — so a hop to a
  dead twin is recoverable rather than sticky.
- **Make the toggle visible on the offer banner.** Replace the second button with a checkbox
  "Always open venue mode at meetings" next to the "Open venue mode" button, reflecting the
  stored value, so you can see whether auto-hop is on and turn it off from either side.
- Keep `venueTwinReachable()` for use on the HTTP twin only (where it works), or drop it.

## Technical notes

- `src/lib/venueMode.ts` — `autoHopToVenue()` drops the `venueTwinReachable()` gate; probe
  helper kept but no longer used on the HTTPS side.
- `src/components/VenueModeBanner.tsx` — auto-hop runs synchronously in the effect when
  `canAutoHop()` is true (render nothing meanwhile); offer state gets the checkbox; in-venue
  state gains a "turn off auto-hop and go back" action.
- `docs/HOW-TO-USE.md` — correct the description of what happens on `ran1.app`.

## Caveat

Without a probe, auto-hop fires whenever a meeting is active and the toggle is on, even off
meeting Wi-Fi. In that case the twin still loads (it's on GitHub Pages, reachable anywhere) —
it just can't read `10.10.10.10`, and its banner offers the way back. That's the trade-off for
a truly zero-tap hop; a pre-flight check is technically impossible from the HTTPS page.
