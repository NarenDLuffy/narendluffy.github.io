# Create the HTTP venue twin on GitHub Pages

Goal: give the app a plain-HTTP copy hosted on GitHub Pages so that, when a delegate is on meeting Wi-Fi, the browser can read `http://10.10.10.10/` for live drafts without mixed-content blocking. The secure main app stays on `https://ran1.app` (Lovable) and offers a one-tap switch to the HTTP twin.

## Good news: `ran1.app` is managed in Lovable

The domain status shows `ran1.app` as a Lovable-managed (`mode: buy`) connected domain. That means you can add DNS records for `venue.ran1.app` directly inside Lovable's domain manager. You do not need to buy another domain or use an external DNS provider.

## Critical constraint: GitHub-provided domains are HTTPS-only

GitHub forces HTTPS on every `*.github.io` domain. You cannot turn it off. That means:

- `https://narendluffy.github.io/` — works, but is HTTPS.
- `http://narendluffy.github.io/` — GitHub redirects to HTTPS.
- An HTTPS page cannot read `http://10.10.10.10/` because of browser mixed-content blocking.

So the venue twin **must** use the custom domain `venue.ran1.app` with HTTPS enforcement disabled.

## Plan

### 1. Back up the existing `narendluffy.github.io` repo

- Go to `https://github.com/narendluffy/narendluffy.github.io`.
- **Settings → General → Repository name**, rename it to `narendluffy.github.io-archive`.

### 2. Create the new RAN1 Live repo named `narendluffy.github.io`

- Create a new public repo called `narendluffy.github.io`.
- Push the current project code to the `main` branch.
- Wait for the deploy workflow to finish. `https://narendluffy.github.io/` will show RAN1 Live.

### 3. Add the `venue.ran1.app` DNS record in Lovable

Because `ran1.app` is managed in Lovable:

1. Open your project in Lovable.
2. Go to **Project Settings → Project section → Domains**.
3. Find `ran1.app`, open the **three-dot menu (⋯)**, and click **Configure**.
4. Click **Manage DNS records**.
5. Add a new record:
   - Type: `CNAME`
   - Name: `venue`
   - Value: `narendluffy.github.io`
   - TTL: leave default
6. Save.

This points only `venue.ran1.app` to GitHub Pages; `ran1.app` itself continues to serve the Lovable-hosted secure app.

### 4. Add the custom domain in GitHub Pages

- In the new `narendluffy.github.io` repo: **Settings → Pages → Custom domain**, enter `venue.ran1.app`.
- Wait for GitHub to verify DNS. This usually takes a few minutes.

### 5. Disable HTTPS enforcement (critical)

- In the same Pages settings, **uncheck** "Enforce HTTPS".
- Without this step, `venue.ran1.app` serves HTTPS and the browser still cannot read `http://10.10.10.10/`.

### 6. Set the `VENUE_HOST` repository variable

- In the repo: **Settings → Secrets and variables → Actions → Variables → New repository variable**.
- Name: `VENUE_HOST`
- Value: `venue.ran1.app`

This tells the deploy workflow to write `venue.ran1.app` into `dist/CNAME` and tells the app where to link for venue mode.

### 7. Re-run the deploy workflow

- Trigger **Actions → Deploy to GitHub Pages → Run workflow**.
- Verify the site loads at `http://venue.ran1.app/` (plain HTTP).

### 8. Update documentation

- Add a "Venue mode" section to `docs/HOW-TO-USE.md` explaining:
  - On meeting Wi-Fi, `https://ran1.app` shows a banner to switch to the HTTP twin.
  - Tapping it opens `http://venue.ran1.app/` and carries bookmarks/follows/read state over.
  - Off-venue, stay on `https://ran1.app` and use the Sync proxy.

## Expected result

- Main app: `https://ran1.app` — secure, uses the Lovable-hosted server function for the 3GPP Sync mirror.
- Venue twin: `http://venue.ran1.app` — plain HTTP, can directly probe `10.10.10.10` when on the meeting LAN.
- The secure app detects mixed-content blocking and offers a one-tap switch to the HTTP twin.

## Notes / caveats

- `narendluffy.github.io` itself will always be HTTPS. Only the attached custom domain `venue.ran1.app` can be HTTP.
- The HTTP twin is the exact same static build as the secure app; only the host and protocol differ.
- If you later want to stop using `venue.ran1.app`, delete the CNAME record in Lovable and remove the custom domain from GitHub Pages.
