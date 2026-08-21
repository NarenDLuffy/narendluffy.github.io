# RAN1 Live

Unofficial meeting-week companion for 3GPP RAN1 delegates.

It turns the frequently changing RAN1 chair and sub-chair DOCX schedules into one
accurate, live, searchable schedule — and (from Phase 3) lets colleagues from the
same verified company voluntarily share which meeting room they are in.

> Schedule information is automatically generated from meeting documents and may
> contain errors. This project is not affiliated with 3GPP.

## Status

- **Phase 1 (this build)** — public schedule frontend: NOW, timetable, My agenda,
  Rooms, Changes, agenda filters, mock RAN1#126 data, GitHub Pages build.
- **Phase 2** — Python DOCX ingestion, source merging/provenance, change detection,
  scheduled GitHub Action refresh.
- **Phase 3** — Supabase auth, verified company domains, RLS-isolated presence and
  coverage.
- **Phase 4** — PWA polish, notifications, floorplan, QR check-in, room stewards.

## Architecture

```
3GPP schedule sources ──► GitHub Actions ──► Python ingestion ──► normalized JSON
                                                                      │
                                                                      ▼
                                                    React frontend on GitHub Pages

React frontend ◄──► Supabase (company users, presence, bookmarks)   [Phase 3]
```

Nothing about a specific meeting is hard-coded: rooms, topics, agenda items and
meeting identity all come from the generated bundle, so RAN1#127, bis and ad-hoc
meetings roll over without frontend changes.

## Schedule sources

- **Public 3GPP source (default).** The only source used by GitHub Actions.
- **Meeting-local source (optional, opt-in).** On the venue network the meeting
  server at `http://10.10.10.10/ftp/RAN/RAN1/Inbox/` often has fresher documents.
  The browser probes it only when the user enables it on the Schedule page, uses it
  only when it is newer, and labels it clearly as **Meeting-local source** while
  keeping full file/version provenance. Hosted runners cannot reach 10.x addresses,
  so builds never depend on it.

## Layout

```
src/            React app (routes, components, services, hooks, types)
public/schedule/ schedule.json · changes.json · sources.json (ingestion output)
ingestion/      Python pipeline (downloader, parser, merger, validator, …)
.github/workflows/ update-schedule.yml · deploy-pages.yml
```

## Development

```bash
bun install
bun run dev
```

## Ingestion

```bash
pip install -r ingestion/requirements.txt
python -m ingestion.generate_schedule          # incremental
python -m ingestion.generate_schedule --force  # full rebuild
```

Deterministic `python-docx` table extraction does the parsing; an LLM is only ever
considered for genuinely ambiguous free text and never resolves a conflict between
two documents. Validation failures keep the previous verified schedule published.

## Deployment

`deploy-pages.yml` builds the static site and publishes it to GitHub Pages, copying
`index.html` to `404.html` so deep links survive a refresh. For a project page set
the repository variable `BASE_PATH` to `/<repo-name>/`; leave it unset for a custom
domain.

## Privacy

No GPS, no browser geolocation, no movement history and no public delegate
directory. Company presence is voluntary, expires automatically, and cross-company
isolation is enforced by Supabase Row Level Security rather than the frontend.
