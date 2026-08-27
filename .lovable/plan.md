# Create the HTTP venue twin on GitHub Pages

Goal: give the app a plain-HTTP copy hosted on GitHub Pages so that, when a delegate is on meeting Wi-Fi, the browser can read `http://10.10.10.10/` for live drafts without mixed-content blocking. The secure main app stays on `https://ran1.app` (Lovable) and offers a one-tap switch to the HTTP twin.

## Important: GitHub Pages forces HTTPS on `*.github.io`

You cannot serve `narendluffy.github.io` over plain HTTP. GitHub always redirects it to HTTPS, and an HTTPS page cannot read `http://10.10.10.10/`. So the venue twin **must** use a custom domain with "Enforce HTTPS" unchecked.

Options for the custom domain:

1. **Recommended:** use a subdomain of `ran1.app` that you already control, e.g. `venue.ran1.app`.
2. **Alternative:** register any cheap domain and point it to GitHub Pages.

The existing `narendluffy.github.io` site can stay as-is, be replaced, or be moved to a project path — it just cannot be the HTTP venue twin.

## What already exists in the repo

- `.github/workflows/deploy-pages.yml` already builds a static export, writes a `CNAME` from the `VENUE_HOST` repository variable, and deploys to GitHub Pages.
- `src/lib/venueMode.ts` already knows how to detect HTTPS-blocked venue access, build the HTTP-twin URL, and carry local state across.
- `src/routes/__root.tsx` and `src/components/VenueModeBanner.tsx` already show the switch banner and consume transferred state.

What is missing is the public GitHub repo, Pages site, custom domain, and DNS record.

## Plan

### 1. Create a public GitHub repository for RAN1 Live

- Create a new public repo under `narendluffy` (e.g. `narendluffy/ran1-live`). Free GitHub Pages only works on public repos.
- Push the current project code to the `main` branch. The existing `.github/workflows/deploy-pages.yml` will run on every push.

### 2. Decide what to do with the existing `narendluffy.github.io` site

Pick one:

- **Leave it alone:** the new repo can be a project site at `https://narendluffy.github.io/ran1-live/`. This is fine for the secure app, but it is still HTTPS-only and cannot be the venue twin.
- **Replace it:** rename the current `narendluffy.github.io` repo to something else, then rename `ran1-live` to `narendluffy.github.io`. This makes RAN1 Live the root site.
- **Use it for the main secure app:** keep `narendluffy.github.io` as the main secure site and only use the custom domain for the venue twin.

For venue mode, the custom-domain path below is what matters.

### 3. Add the custom domain in your DNS

If using `venue.ran1.app`:

- Go to your DNS provider for `ran1.app`.
- Add a `CNAME` record:
  - Name: `venue`
  - Value: `narendluffy.github.io`

If using a different domain, point its apex/subdomain CNAME to `narendluffy.github.io`.

### 4. Configure the custom domain in GitHub Pages

- In the `ran1-live` repo: **Settings → Pages → Custom domain**, enter `venue.ran1.app` (or your chosen domain).
- GitHub will verify the DNS record. This can take a few minutes.

### 5. Disable HTTPS enforcement (critical)

- In the same Pages settings, **uncheck** "Enforce HTTPS".
- This is the only way GitHub Pages will serve `http://venue.ran1.app/`. With HTTPS enforced, the browser would be redirected to `https://` and venue-server reads would still be blocked.

### 6. Set the `VENUE_HOST` repository variable

- In the repo: **Settings → Secrets and variables → Actions → Variables → New repository variable**.
- Name: `VENUE_HOST`
- Value: `venue.ran1.app` (or your chosen domain)

This tells the deploy workflow to write the domain into `dist/CNAME` and tells the app where to link for venue mode.

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

- `github.io` domains cannot be served over plain HTTP; GitHub forces HTTPS on them. That is why a custom domain is required.
- If you do not control DNS for `ran1.app`, you need to either get access or register a new domain for the venue twin.
- The HTTP twin is the exact same static build as the secure app; only the host and protocol differ.
