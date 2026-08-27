# Create the HTTP venue twin on GitHub Pages

Goal: give the app a plain-HTTP copy hosted on GitHub Pages so that, when a delegate is on meeting Wi-Fi, the browser can read `http://10.10.10.10/` for live drafts without mixed-content blocking. The secure main app stays on `https://ran1.app` (Lovable) and offers a one-tap switch to the HTTP twin.

## Critical constraint: GitHub-provided domains are HTTPS-only

GitHub forces HTTPS on every `*.github.io` domain. You cannot turn it off. That means:

- `https://narendluffy.github.io/` — works, but is HTTPS.
- `http://narendluffy.github.io/` — GitHub redirects to HTTPS.
- An HTTPS page cannot read `http://10.10.10.10/` because of browser mixed-content blocking.

So **you cannot use the GitHub-provided domain for venue mode**. You must attach a custom domain and disable HTTPS enforcement on it.

## Your options for the custom domain

### Option A: Use a subdomain of `ran1.app` (cheapest, if you control its DNS)

If you can edit DNS for `ran1.app`, create `venue.ran1.app` for free. It points to the same GitHub Pages site; only the DNS record changes.

### Option B: Register a new cheap domain

Examples:

- `ran1venue.com`
- `ran1livevenue.net`
- `ran1meet.app`

A `.com` or `.net` domain usually costs $10–15/year. A `.app` or `.dev` domain forces HTTPS at the TLD level, so avoid those. Stick with `.com`, `.net`, `.org`, `.info`, etc.

### Option C: Skip venue mode and use the Sync proxy only

The app already has a server-side proxy for the public 3GPP Sync mirror. If you never need live venue-server access, you can deploy to `narendluffy.github.io` over HTTPS and the Drafts tab will still update from the Sync mirror. You just lose the ability to read `10.10.10.10` directly from the browser.

## What already exists in the repo

- `.github/workflows/deploy-pages.yml` already builds a static export, writes a `CNAME` from the `VENUE_HOST` repository variable, and deploys to GitHub Pages.
- `src/lib/venueMode.ts` already knows how to detect HTTPS-blocked venue access, build the HTTP-twin URL, and carry local state across.
- `src/routes/__root.tsx` and `src/components/VenueModeBanner.tsx` already show the switch banner and consume transferred state.

## Plan (assuming you get a custom domain)

### 1. Choose and obtain the domain

Pick one of the options above. For this plan, examples use `venue.ran1.app`; replace with your actual domain.

### 2. Back up the existing `narendluffy.github.io` repo

- Go to `https://github.com/narendluffy/narendluffy.github.io`.
- **Settings → General → Repository name**, rename it to `narendluffy.github.io-archive`.

### 3. Create the new RAN1 Live repo named `narendluffy.github.io`

- Create a new public repo called `narendluffy.github.io`.
- Push the current project code to the `main` branch.
- Wait for the deploy workflow to finish. `https://narendluffy.github.io/` will show RAN1 Live.

### 4. Add the DNS record

For `venue.ran1.app`:

- In your DNS provider for `ran1.app`, add a `CNAME`:
  - Name: `venue`
  - Value: `narendluffy.github.io`

For a new domain:

- Point the apex domain using GitHub's A records, or point a subdomain CNAME to `narendluffy.github.io`.

### 5. Add the custom domain in GitHub Pages

- In the new repo: **Settings → Pages → Custom domain**, enter your domain (e.g. `venue.ran1.app`).
- Wait for GitHub to verify DNS.

### 6. Disable HTTPS enforcement (critical)

- In the same Pages settings, **uncheck** "Enforce HTTPS".
- Without this step, the domain serves HTTPS and venue mode still fails.

### 7. Set the `VENUE_HOST` repository variable

- In the repo: **Settings → Secrets and variables → Actions → Variables → New repository variable**.
- Name: `VENUE_HOST`
- Value: your custom domain, e.g. `venue.ran1.app`

### 8. Re-run the deploy workflow

- Trigger **Actions → Deploy to GitHub Pages → Run workflow**.
- Verify the site loads at `http://venue.ran1.app/` (plain HTTP).

### 9. Update documentation

- Add a "Venue mode" section to `docs/HOW-TO-USE.md` explaining:
  - On meeting Wi-Fi, `https://ran1.app` shows a banner to switch to the HTTP twin.
  - Tapping it opens `http://venue.ran1.app/` and carries bookmarks/follows/read state over.
  - Off-venue, stay on `https://ran1.app` and use the Sync proxy.

## Expected result

- Main app: `https://ran1.app` — secure, uses Lovable server function for the 3GPP Sync mirror.
- Venue twin: `http://venue.ran1.app` — plain HTTP, can directly probe `10.10.10.10` on the meeting LAN.
- The secure app detects mixed-content blocking and offers a one-tap switch to the HTTP twin.

## If you choose not to get a custom domain

- Deploy to `narendluffy.github.io` over HTTPS.
- The app works normally for schedules, agenda, and drafts via the Sync proxy.
- Venue-server live probing is disabled; the Drafts tab falls back to the Sync mirror and the published snapshot.
- Update `src/lib/venueMode.ts` so the banner explains that venue mode is unavailable without a custom domain.
