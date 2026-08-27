# Always-on venue mode + fix the GitHub Pages build

Two things: make `https://ran1.app` hop to the venue twin automatically, and unblock the failing Pages deploy.

## 1. Fix the failing build (confirmed cause)

The build log shows the failing step is the post-build guard:

```text
dist/client/assets/index-*.js: build output contains forbidden string "sb_secret_"
```

This is a false positive. The guard looks for the bare prefix `sb_secret_`, and three
auto-generated backend client files contain a key-format check
(`value.startsWith('sb_secret_')`) that ends up in the bundle. No actual secret is shipped.

Fix in `scripts/check-public-data.mjs`: match a real key value rather than the prefix —
require the prefix followed by a plausible key body (e.g. at least 12 key characters) —
so `startsWith('sb_secret_')` no longer trips it while a leaked key still does. Same
treatment for any other prefix-only rules in that list. The generated Supabase files are
not touched.

Also in `.github/workflows/deploy-pages.yml`: silence the Node 20 deprecation warning by
moving to the current action versions (`actions/checkout@v5`, `upload-pages-artifact@v4`,
`deploy-pages@v4`).

## 2. "Always open venue mode" toggle

Goal: only ever type `https://ran1.app`; when the meeting-room server is reachable the app
sends you to `http://3gpplive.net` by itself, silently.

Behaviour:

- New toggle in Settings/the venue banner: **Always open venue mode** (device-local, already
  backed by the existing `alwaysSwitch()` storage key).
- On app start on the HTTPS host, when the toggle is on and no previous hop has failed, run a
  short reachability probe, then redirect immediately with no banner or confirmation
  (`window.location.replace`, so Back doesn't bounce).
- Follows, bookmarks and preferences travel across in the existing transfer blob.
- The existing failed-hop guard stays: if the browser upgrades the hop to HTTPS, the device is
  marked as failed, auto-hop switches off, and the banner explains why instead of looping.
- On the HTTP twin, the toggle is shown as active with a "back to secure site" link.

### Reachability probe

Because an HTTPS page cannot fetch `http://10.10.10.10` at all, "reachable" is decided
without touching the venue IP:

- Fire a no-cors probe at the twin host (`http://3gpplive.net/favicon.png`) with a ~1.5s
  timeout; if it answers, the hop is worthwhile.
- Never auto-hop on `localhost`, when `VENUE_HOST` is empty, or when the hop is marked failed.
- Once on the twin, the existing venue probe against `10.10.10.10` runs as it does today; if
  it fails there, the banner offers a one-tap return to the secure host and clears the toggle
  so you are not stuck on the HTTP twin.

## Files touched

- `scripts/check-public-data.mjs` — precise secret matching
- `.github/workflows/deploy-pages.yml` — action version bumps
- `src/lib/venueMode.ts` — auto-hop decision + probe helper
- `src/components/VenueModeBanner.tsx` — toggle UI, silent-hop path, return link
- `docs/HOW-TO-USE.md` — short note on the toggle
