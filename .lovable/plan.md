# Create the HTTP venue twin on GitHub Pages

Goal: give the app a plain-HTTP copy hosted on GitHub Pages so that, when a delegate is on meeting Wi-Fi, the browser can read `http://10.10.10.10/` for live drafts without mixed-content blocking. The secure main app stays on `https://ran1.app` (Lovable) and offers a one-tap switch to the HTTP twin.

## Your chosen approach

Replace the existing `narendluffy.github.io` repository with the RAN1 Live app, then attach `venue.ran1.app` as a custom domain. This works — the custom domain is what enables plain HTTP, not the repository name.

Important notes:

- `narendluffy.github.io` itself will still be served over HTTPS by GitHub; you cannot change that.
- `venue.ran1.app` can be served over HTTP once you uncheck "Enforce HTTPS" in Pages settings.
- So the venue URL you will actually use is `http://venue.ran1.app/`, not `http://narendluffy.github.io/`.

## What already exists in the repo

- `.github/workflows/deploy-pages.yml` already builds a static export, writes a `CNAME` from the `VENUE_HOST` repository variable, and deploys to GitHub Pages.
- `src/lib/venueMode.ts` already knows how to detect HTTPS-blocked venue access, build the HTTP-twin URL, and carry local state across.
- `src/routes/__root.tsx` and `src/components/VenueModeBanner.tsx` already show the switch banner and consume transferred state.

What is missing is the public GitHub repo setup, the custom domain DNS, and the HTTPS-off setting.

## Plan

### 1. Back up the existing `narendluffy.github.io` repo

- Go to the repo on GitHub: `https://github.com/narendluffy/narendluffy.github.io`.
- **Settings → General → Repository name**, rename it to something like `narendluffy.github.io-archive`.
- This frees up the `narendluffy.github.io` name and keeps your old site available.

### 2. Create the new RAN1 Live repo named `narendluffy.github.io`

- Create a new public repo called `narendluffy.github.io`.
- Push the current project code to the `main` branch.
- The existing `.github/workflows/deploy-pages.yml` will run and deploy the site.
- After a few minutes, `https://narendluffy.github.io/` will show RAN1 Live.

### 3. Add the `venue.ran1.app` DNS record

- Go to your DNS provider for `ran1.app`.
- Add a `CNAME` record:
  - Name: `venue`
  - Value: `narendluffy.github.io`

### 4. Add the custom domain in GitHub Pages

- In the new `narendluffy.github.io` repo: **Settings → Pages → Custom domain**, enter `venue.ran1.app`.
- GitHub will verify the DNS record. This can take a few minutes.

### 5. Disable HTTPS enforcement (critical)

- In the same Pages settings, **uncheck** "Enforce HTTPS".
- This is the only way GitHub Pages will serve `http://venue.ran1.app/`. With HTTPS enforced, the browser would be redirected to `https://` and venue-server reads would still be blocked.

### 6. Set the `VENUE_HOST` repository variable

- In the repo: **Settings → Secrets and variables → Actions → Variables → New repository variable**.
- Name: `VENUE_HOST`
- Value: `venue.ran1.app`

This tells the deploy workflow to write `venue.ran1.app` into `dist/CNAME` and tells the app where to link for venue mode.

### 7. Re-run the deploy workflow

- Trigger **Actions → Deploy to GitHub Pages → Run workflow**.
- Verify the site loads at `http://venue.ran1.app/` (not `https://`).

### 8. Update documentation

- Add a short "Venue mode" section to `docs/HOW-TO-USE.md` explaining:
  - When on meeting Wi-Fi, the secure app shows a banner offering the HTTP twin.
  - Tapping it opens `http://venue.ran1.app/` with bookmarks/follows carried over.
  - When not at the venue, stay on `https://ran1.app`; it uses the server-side Sync proxy instead.

## Expected result

- Main app: `https://ran1.app` — always secure, uses the Lovable-hosted server function for the 3GPP Sync mirror.
- Venue twin: `http://venue.ran1.app` — plain HTTP, can directly probe `10.10.10.10` when on the meeting LAN.
- Switching: the secure app detects it is blocked from reading `10.10.10.10` and shows a banner: "Switch to venue mode". Tapping it carries `localStorage` state to the HTTP twin.

## Notes / caveats

- `narendluffy.github.io` itself will always be HTTPS. Only the attached custom domain `venue.ran1.app` can be HTTP.
- If you do not control DNS for `ran1.app`, register a new cheap domain and replace `venue.ran1.app` with it throughout.
- The HTTP twin is the exact same static build as the secure app; only the host and protocol differ.
