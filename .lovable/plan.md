# Create the HTTP venue twin on GitHub Pages

Goal: give the app a plain-HTTP copy hosted on GitHub Pages so that, when a delegate is on meeting Wi-Fi, the browser can read `http://10.10.10.10/` for live drafts without mixed-content blocking. The secure main app stays on `https://ran1.app` (Lovable) and offers a one-tap switch to the HTTP twin.

## What already exists in the repo

- `.github/workflows/deploy-pages.yml` already builds a static export, writes a `CNAME` from the `VENUE_HOST` repository variable, and deploys to GitHub Pages.
- `src/lib/venueMode.ts` already knows how to detect HTTPS-blocked venue access, build the HTTP-twin URL, and carry local state across.
- `src/routes/__root.tsx` and `src/components/VenueModeBanner.tsx` already show the switch banner and consume transferred state.

What is missing is the actual public GitHub repo, Pages site, and DNS record for the subdomain.

## Plan

### 1. Create a public GitHub repository and push the code

- Create a new public repo under your GitHub account (e.g. `karlla1220/ran1-live`). Free GitHub Pages only works on public repos.
- Push the current project code to the `main` branch. The existing `.github/workflows/deploy-pages.yml` will run on every push.

### 2. Enable GitHub Pages

- In the repo: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
- The first run will deploy to the default `github.io` URL. Wait for it to finish.

### 3. Add the `venue.ran1.app` subdomain in your DNS

Because `ran1.app` currently points to Lovable, you only need to add one record for the subdomain:

- Type: `CNAME`
- Name: `venue` (or `venue.ran1.app.` depending on your DNS provider)
- Value: `<your-github-username>.github.io` (replace with your actual GitHub username or org name)

Example: if your GitHub username is `karlla1220`, the value is `karlla1220.github.io`.

### 4. Configure the custom domain in GitHub Pages

- In the repo: **Settings → Pages → Custom domain**, enter `venue.ran1.app`.
- GitHub will verify the DNS record. This can take a few minutes after step 3.

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
- Switching: the secure app detects it is blocked from reading `10.10.10.10` and shows a banner: "Switch to venue mode". Tapping it carries `localStorage` state (bookmarks, follows, read state) to the HTTP twin.

## Notes / caveats

- `github.io` domains cannot be served over plain HTTP; GitHub forces HTTPS on them. That is why a custom subdomain is required.
- If you later stop using `ran1.app`, you can point the apex domain to GitHub Pages instead and use a different subdomain for the venue twin.
- The HTTP twin is the exact same static build as the secure app; only the host and protocol differ.
