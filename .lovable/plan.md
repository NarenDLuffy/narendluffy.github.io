# Fix: move the venue twin off ran1.app to a separate HTTP-capable domain

## Root cause (verified against live hosts)

- `http://venue.ran1.app/` returns **HTTP 200 from GitHub with no redirect** — GitHub Pages is set up correctly.
- `https://ran1.app/` sends `strict-transport-security: max-age=31536000; includeSubDomains`. Any browser that has ever loaded ran1.app refuses plain HTTP for **every subdomain**, including `venue.ran1.app`, for a year. The browser upgrades the request internally; GitHub never sees HTTP.
- `https://venue.ran1.app/` also sends GitHub's own HSTS header, so any single HTTPS visit to the twin pins that host too.

Conclusion: the venue twin cannot live under `ran1.app`, and Option B (weakening HSTS on the main site) is not worth the security loss and may not even be grantable by Lovable support.

## Plan: Option A — separate domain for the twin

### Why an external registrar, not a Lovable-bought domain

Lovable can sell you a domain, but it auto-connects to this project and is served over HTTPS by Lovable's edge with the same HSTS policy — the same trap, new name. The twin needs a domain whose DNS points **only** at GitHub Pages, with no Lovable HTTPS serving anywhere on it.

### Steps for you (manual, one time)

1. **Buy a cheap second domain** at an external registrar (Namecheap, Cloudflare, Porkbun, etc.). Suggestion: `ran1live.net` or similar — roughly €8–12/year. It does not need to look pretty; it is only used on the meeting LAN.
2. **Add DNS at that registrar:**
   - To use the apex (`ran1live.net`): A records pointing to GitHub Pages' IPs: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`.
   - Or a subdomain (`venue.ran1live.net`): CNAME to `narendluffy.github.io`.
3. **GitHub repo** → Settings → Pages → Custom domain: enter the new hostname, keep **"Enforce HTTPS" unchecked**.
4. **Repo variable:** Settings → Secrets and variables → Actions → Variables → set `VENUE_HOST` to the new hostname.
5. **Re-run** Actions → Deploy to GitHub Pages.
6. **Remove** `venue.ran1.app` from GitHub Pages custom domain settings, and delete the `venue` CNAME record from the ran1.app DNS manager in Lovable (Domains → ran1.app → ⋯ → Configure → Manage DNS records).
7. Verify: `curl -I http://<new-host>/` returns 200 with no redirect, and open `http://<new-host>/` in a browser that has never seen its HTTPS version.

### Rule going forward

Only ever link to the twin as an explicit `http://` URL. Never open its `https://` version — GitHub's HSTS header would pin it for that browser for a year.

### Code changes (I will implement on approval)

1. `src/lib/venueMode.ts` — change the `VENUE_HOST` fallback default away from `venue.ran1.app` so a missing repo variable never points at the broken host.
2. `src/components/VenueModeBanner.tsx` — add failed-hop detection: if the user arrived with the `ran1import` transfer parameter but the page is on `https:`, the browser silently upgraded. Show a clear "venue mode was blocked by your browser" message with a direct `http://` link to copy/paste, instead of silently falling back.
3. `src/lib/venueMode.ts` — record a failed hop and suppress `alwaysSwitch` auto-redirect afterwards, so users are never bounced between hosts in a loop.
4. `docs/HOW-TO-USE.md` and `README.md` — replace `venue.ran1.app` references with the new host and add a one-line note that the twin must stay on a separate domain because of HSTS.

## Out of scope

- No changes to the main site's security headers.
- No change to drafts/schedule pipelines.
