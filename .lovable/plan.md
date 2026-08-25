# Keep private data out of the build, ship on GitHub Pages, and document it

Three pieces of work: a hard guarantee that company-presence and any future
sensitive data never ends up in the public bundle, a clean GitHub Pages
deployment on a free `github.io` URL, and documentation for you and your
colleagues.

## 1. Never bundle sensitive data

Today presence lives only in the browser's local storage (`presenceService.ts`),
so nothing sensitive is shipped. The goal is to make that permanent and
enforced, not just true by accident.

- **Written rule.** A short `docs/data-classification.md` defining three tiers:
  public (schedule, rooms, drafts index), device-only (bookmarks, follows,
  display name, presence), and secret (never in the repo at all).
- **Single boundary.** Keep `presenceService.ts` as the only module that touches
  presence storage, so a future shared backend swaps the store without any
  component learning about it. Add a header comment stating that any remote
  presence store must be fetched at runtime and never imported into build data.
- **Automated guard.** A `scripts/check-public-data.mjs` script run before every
  build and in CI that fails the build if:
  - any file under `public/` contains a presence/company payload shape
    (`presence`, `checkins`, `attendees`, `email`, `@company` patterns),
  - a file matching `*.private.*`, `*.secret.*`, or `.env*` sits under `public/`,
  - the built output contains any string from a denylist of sensitive keys.
- **Ignore rules.** `.gitignore` entries for `public/**/*.private.json`,
  `**/presence*.json`, and local scratch data so those can never be committed.

## 2. GitHub Pages setup (free `username.github.io/repo`)

- Confirm the build emits a fully static site (client HTML/JS/CSS with no server
  runtime requirement); adjust the build config if the current output is a
  server bundle, and prerender the routes so deep links have real HTML.
- `.github/workflows/deploy-pages.yml` already builds and deploys; it gets:
  - `BASE_PATH` wired to the repo name automatically (falls back to `/` for a
    custom domain), so assets resolve at `username.github.io/repo-name/`,
  - the public-data guard step before upload,
  - the existing `404.html` + `.nojekyll` SPA fallback kept.
- All in-app links and fetches of `/data/...` JSON go through the Vite base URL
  so they work under a sub-path, not just at the domain root.
- Repo checklist in the README: make repo public, Settings → Pages → Source
  "GitHub Actions", push to `main`, done. Later, if you drop `ran1.app`, nothing
  changes — the `github.io` URL is the primary one.

## 3. Documentation

- **`README.md`** rewritten: what RAN1 Live is, current feature set (live
  schedule from 3GPP portal + Inbox DOCX parsing, drafts tracker with venue
  10.10.10.10 / SYNC probing, My agenda, rooms, changes), architecture diagram,
  how the ingestion pipelines run, local dev commands, deployment steps, data
  classification and privacy statement, disclaimer that it is unofficial.
- **`docs/HOW-TO-USE.md`** written for delegates, not developers: a short tour of
  each tab (Now, Timetable, Schedule, My agenda, Drafts, Rooms, Changes,
  Meetings), how to bookmark and follow agenda items, how "Refresh now" and the
  venue-server probe work, how to export to calendar, that everything you mark is
  stored only on your own device, and known limitations. Linked from the README
  and from an in-app "How to use" link in the app menu.

## Technical notes

- Guard script is plain Node, wired as a `prebuild`/CI step — no new deps.
- No backend or account system is introduced; presence stays device-local.
- The static-output check is the only item that may require a build-config
  change; everything else is additive.
