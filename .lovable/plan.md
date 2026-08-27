# Hosting decision: ran1.app vs GitHub Pages

## Why ran1.app exists at all

`ran1.app` is the Lovable-hosted deployment. It is not just a domain — it is the only place where the **server-side parts** of the app can run.

The app currently has three layers:

```text
Browser (React/Vite static build)
  ├─ reads public schedule/drafts from 3GPP / GitHub
  ├─ talks to local meeting server http://10.10.10.10 (only in venue mode)
  └─ reads/writes shared company presence

Server functions (createServerFn)
  └─ validate company codes and write presence to Supabase

Database (Supabase)
  └─ stores company_presence rows so every colleague sees the same room list
```

GitHub Pages can only serve the **top layer** — the static browser build. It cannot run server functions or hold secrets, so it cannot write to Supabase with the privileges needed for shared presence.

## What breaks if you move everything to GitHub Pages

| Feature | On ran1.app | On GitHub Pages only |
| --- | --- | --- |
| Public schedule | Works | Works |
| Drafts tracker | Works | Works |
| My agenda / ICS export | Works | Works |
| Venue-mode draft probing from 10.10.10.10 | Works via separate HTTP twin | Needs a separate non-HTTPS domain; GitHub Pages custom domains usually force HTTPS |
| **Shared company presence** (who checked in) | Works via Supabase | Falls back to **local-only** — each device only sees itself |
| Automatic meeting rollover / backend cron | Works | Must rely only on client-side or GitHub Actions polling |
| Managed previews / instant rollbacks | Lovable provides them | Not available |

## The real purpose of ran1.app today

1. **Shared presence backend** — the only feature that genuinely needs a server.
2. **Convenience** — automatic deploys, preview URLs, SSL, and the custom domain you already configured.
3. **Venue twin anchor** — the secure "main" site that links to the plain-HTTP venue copy.

## Options

### Option A — Keep both (recommended, current setup)

- `ran1.app` = main secure app with shared presence.
- GitHub Pages = plain-HTTP venue twin for meeting-room Wi-Fi.
- Cost after the first year: only the `ran1.app` domain renewal. The GitHub Pages site is free.

### Option B — GitHub Pages as primary, drop ran1.app

- Move the main app to `narendluffy.github.io` (or a custom domain on GitHub Pages).
- Shared presence becomes local-only. Everyone sees only their own check-in.
- Venue mode still needs a **second, non-HTTPS domain** (not a subdomain of the main site, because HSTS would pin it to HTTPS). You would host the same GitHub Pages build there with "Enforce HTTPS" unchecked.
- You lose Lovable-managed previews and instant rollbacks, but hosting is free.

### Option C — GitHub Pages only, no venue mode

- Same as B, but you accept that venue draft probing from 10.10.10.10 does not work.
- Users must manually fetch drafts from the public 3GPP mirror instead of the meeting-room server.
- Simplest and cheapest, but weakens the in-room experience.

## What I recommend

Keep Option A unless the annual domain cost is the deciding factor. The value of `ran1.app` is not the domain itself — it is the shared presence backend and the managed hosting around it. If you still want to drop it, pick Option B and accept local-only presence.

## Decision needed

Please confirm which option you want, and I will implement the corresponding changes (or leave the current setup untouched if you choose A).