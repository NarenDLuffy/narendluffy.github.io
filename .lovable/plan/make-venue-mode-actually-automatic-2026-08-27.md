# Make venue mode actually automatic

## The problem in plain language

You open `https://ran1.app` during a meeting and still see the **Open venue mode** banner instead of being sent to the venue twin automatically.

There are two reasons:

1. **The "always" switch is probably off.** The banner has two buttons but no checkbox in the offer state, so it's not obvious whether auto-hop is enabled. If you only ever tapped **Open venue mode**, the app never stored the "always" preference, so it asks again every time.
2. **Even with the switch on, the current auto-hop can't work.** Before hopping, the app tries to fetch `http://3gpplive.net/favicon.png` from the HTTPS page. Browsers block any HTTP subresource request from an HTTPS page (mixed-content). The probe always fails, so the app falls back to showing the banner.

The fix is to stop probing and just hop. A top-level navigation from an HTTPS page to an HTTP URL is allowed — that's exactly what the **Open venue mode** button already does successfully.

## What will change

- **Auto-hop becomes instant.** When a meeting is active, the toggle is on, and the hop isn't marked failed, the HTTPS page calls `window.location.replace(venueModeUrl())` immediately. No banner flash, no probe.
- **The offer banner gets a visible checkbox.** Next to **Open venue mode** you'll see **Always open venue mode at meetings**, checked or unchecked, so you can tell and change the preference from either side.
- **Safety net stays in place.** If the browser upgrades the hop to HTTPS (HSTS), the twin marks the device as failed and stops auto-hopping. If you land on the twin but the meeting-room server isn't reachable, the twin offers a one-tap **Back to ran1.app** and turns the toggle off so you don't get stuck.
- **The long `?ran1import=...` URL is cleaned immediately.** The twin reads the blob once, writes the transferred settings into its own localStorage, and removes the parameter from the address bar with `history.replaceState`. Users only see it for the split second of the hop.

## About the `https://3gpplive.net` worry

Because GitHub Pages has **Enforce HTTPS unchecked** for the twin, visiting `https://3gpplive.net` by accident will load over HTTPS but should not pin HSTS. The app itself only ever navigates to `http://3gpplive.net`. To be extra safe, the twin page can detect when it loaded over HTTPS and show a warning instead of functioning normally, reminding the user to go through `ran1.app`.

## Files to touch

- `src/lib/venueMode.ts` — remove the probe gate from `autoHopToVenue()`.
- `src/components/VenueModeBanner.tsx` — instant auto-hop in the effect; checkbox in the offer state; HTTPS-on-twin warning.
- `docs/HOW-TO-USE.md` — update the venue-mode description.

## Note on `ran1.net`

A separate alias domain would need its own GitHub Pages custom-domain slot and would still have to be served plain-HTTP. It doesn't remove the mixed-content restriction or the need for the import blob. Keeping `3gpplive.net` as the twin and making the hop silent is the simplest path; the user never needs to type or bookmark the twin address.
