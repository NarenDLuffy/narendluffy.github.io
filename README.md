# RAN1 Live

Unofficial, mobile-first meeting-week companion for 3GPP RAN1 delegates.

It turns the frequently changing RAN1 chair and sub-chair schedule documents into
one accurate, searchable, live schedule — and tracks draft / FL-summary activity
in the meeting Inbox as it happens.

> Schedule and draft information is generated automatically from public 3GPP
> meeting documents and may contain errors. This project is not affiliated with
> or endorsed by 3GPP.

**For delegates:** see [How to use this website](docs/HOW-TO-USE.md).

## Features

- **Automatic meeting discovery** — the meeting registry is built from the
  official 3GPP portal web service, so every future RAN1 meeting appears without
  a code change. The current meeting is selected by priority: in progress →
  upcoming → most recent completed.
- **Live schedule** — chair/sub-chair `.docx` schedules are discovered
  recursively under the meeting's `Inbox/`, parsed as a block grid (rooms,
  parallel tracks, per-agenda-item minute breakdowns, coffee/lunch bands) and
  merged with provenance per source document.
- **Now / Timetable / Search** — what is running right now, a fixed
  08:30–19:30 day grid with parallel tracks, and agenda/topic filters.
- **My agenda** — bookmark sessions and agenda items, export `.ics`.
- **Drafts tracker** — the entire Inbox directory tree is discovered
  recursively (no hard-coded folder names), files are mapped to agenda items by
  ancestor traversal, and new/updated files raise unread counts. The browser
  probes the venue server `10.10.10.10` first, falls back to the
  `Meetings_3GPP_SYNC` mirror, then to the last published snapshot, and
  de-duplicates the same file arriving on multiple servers.
- **Rooms & changes** — per-room day views and a diff feed of moved sessions,
  room changes and agenda edits.
- **Company presence (optional)** — account-free, voluntary, device-local room
  check-ins scoped to one meeting, expiring after two hours.
- **Offline-friendly PWA** — last good bundle cached, stale banner, installable.

## Architecture

```
3GPP portal web service ─┐
3GPP FTP (Inbox/*.docx) ─┼─► GitHub Actions ─► Python ingestion ─► public/data/*.json
3GPP FTP (draft tree)   ─┘                      (ingestion/, draft_tracker/)
                                                             │
                                                             ▼
                                     React + TanStack Start static build
                                                             │
                                     ┌────────────────────────┴────────────────────────┐
                                     ▼                                                   ▼
                            https://ran1.app (Lovable)                    http://<venue-host> (GitHub Pages)
                                     │                                                   │
                   server function proxy for SYNC mirror              direct read of 10.10.10.10 on meeting LAN
                                     │
                   browser also probes 10.10.10.10 when possible
```

The main app is served by Lovable over HTTPS and uses a server function to crawl
the public 3GPP SYNC mirror. Because browsers block HTTPS pages from fetching
HTTP URLs, a separate plain-HTTP copy is hosted on GitHub Pages for use on the
meeting Wi-Fi; that copy can read the venue server `10.10.10.10` directly.

The twin's hostname is supplied at build time via the `VENUE_HOST` repository
variable (`VITE_VENUE_HOST`). It **must be its own separate domain, not a
subdomain of the main site**: `ran1.app` sends HSTS with `includeSubDomains`,
so any browser that has visited the main site silently upgrades every
`*.ran1.app` request to HTTPS before it leaves the device — a twin under
`ran1.app` can never be reached over plain HTTP. Also avoid opening the twin's
`https://` version: GitHub Pages sends its own HSTS header there, which would
pin the twin host for that browser.

- `ingestion/` — portal discovery, FTP crawling, DOCX block-schedule parsing,
  merging, validation, change detection.
- `draft_tracker/` — recursive directory-tree crawl, agenda mapping, snapshot
  diffing.
- `src/` — React frontend. Data access is isolated in `src/services/`.
- `public/data/` — generated public JSON bundles, committed by the workflows.

## Local development

```bash
bun install
bun run dev            # http://localhost:8080
bun run build          # static build (runs the public-data guard first)
bun run check:public-data
bun run lint
```

Python pipelines:

```bash
python -m ingestion.live            # refresh meeting + schedule bundles
python -m draft_tracker.crawl       # refresh the draft index
```

## Scheduled updates

| Workflow | What it does | When |
| --- | --- | --- |
| `.github/workflows/update-schedule.yml` | Re-discovers meetings and re-parses schedules | frequently during a meeting week, sparsely otherwise |
| `.github/workflows/update-drafts.yml` | Re-crawls the Inbox tree and diffs snapshots | every 10 min during meetings |
| `.github/workflows/deploy-pages.yml` | Builds and deploys the site | on every push to `main` |

## Deploying to GitHub Pages

The site is a static build — no server required, free forever on `github.io`.

1. Make the repository **public** (free GitHub Pages requires this).
2. **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. Push to `main`. The deploy workflow builds, runs the data guard, adds the SPA
   `404.html` fallback and `.nojekyll`, and publishes.
4. Your site is live at `https://<username>.github.io/<repo>/`.

The workflow resolves the base path automatically:

- project site → `/<repo>/`
- `<username>.github.io` repo or a `CNAME` file present → `/`
- override with a `BASE_PATH` repository variable if needed

Because of this, dropping a custom domain later needs no code change: delete the
`CNAME` and the next deploy serves correctly from the `github.io` sub-path.

## Privacy & data classification

Everything published is public 3GPP information. Bookmarks, follows, read state,
display name and room presence never leave the device. The rules and the build
guard that enforces them are documented in
[docs/data-classification.md](docs/data-classification.md);
`scripts/check-public-data.mjs` fails the build if private data would be shipped.

## Licence / disclaimer

Community project, provided as-is. Always confirm against the official chair
notes before relying on a time or room.
