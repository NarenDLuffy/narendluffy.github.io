# Finish Option A with 3gpplive.net as the HTTP venue twin

## Goal

Keep `https://ran1.app` as the main secure app (Lovable-hosted, with shared company presence), and make `http://3gpplive.net` the plain-HTTP venue twin on GitHub Pages so browsers on meeting Wi-Fi can read `http://10.10.10.10/` for live drafts.

## Why a separate domain is required

`ran1.app` sends `Strict-Transport-Security: max-age=31536000; includeSubDomains`. Any browser that has visited it will force every `*.ran1.app` address to HTTPS for a year, including `venue.ran1.app`. That is why `http://venue.ran1.app` keeps becoming `https://venue.ran1.app`. A completely separate domain (`3gpplive.net`) avoids this.

## Steps for you (manual, one time)

### 1. DNS at your 3gpplive.net registrar

Add these DNS records. They point the apex domain at GitHub Pages' four load-balancer IPs:


| Type | Name | Value           |
| ---- | ---- | --------------- |
| A    | @    | 185.199.108.153 |
| A    | @    | 185.199.109.153 |
| A    | @    | 185.199.110.153 |
| A    | @    | 185.199.111.153 |


If your registrar supports an "Apex flattening" / ALIAS option, you can use that instead, but the four A records above work everywhere. TTL can be left at the default.

Wait a few minutes, then verify with:

```text
nslookup 3gpplive.net
```

You should see the four GitHub IPs above.

### 2. GitHub Pages custom domain

1. Go to your repo: `https://github.com/narendluffy/narendluffy.github.io`.
2. Open **Settings → Pages → Custom domain**.
3. Enter `3gpplive.net` and click Save.
4. **Uncheck "Enforce HTTPS"**. This is required; without it the twin serves HTTPS and cannot fetch `http://10.10.10.10/`.
5. Wait for GitHub to verify DNS (usually a few minutes, can take up to an hour).

### 3. Set the VENUE_HOST repository variable

1. In the same repo: **Settings → Secrets and variables → Actions → Variables**.
2. Click **New repository variable**.
3. Name: `VENUE_HOST`
4. Value: `3gpplive.net`
5. Save.

This tells the deploy workflow to write `3gpplive.net` into `dist/CNAME` and tells the app where to link for venue mode.

### 4. Re-run the deploy workflow

1. Go to **Actions → Deploy to GitHub Pages**.
2. Click **Run workflow**.
3. Wait for it to finish.

### 5. Clean up the broken venue.ran1.app records

1. In the repo's **Pages settings**, remove `venue.ran1.app` from the custom domain field if it is still there.
2. In Lovable: **Project Settings → Project section → Domains → ran1.app → ⋯ → Configure → Manage DNS records**.
3. Delete the `venue` CNAME record that pointed to `narendluffy.github.io`.

`ran1.app` and `www.ran1.app` should stay exactly as they are — they are the main secure app.

## Verification

1. Open `http://3gpplive.net/` in a browser (type it explicitly, do not rely on search suggestions). It should load over plain HTTP with no redirect to HTTPS.
2. On a device connected to meeting Wi-Fi, open `http://3gpplive.net/`.
3. Go to the **Drafts** tab and tap **Refresh now**. It should be able to read `http://10.10.10.10/` and show the latest venue drafts.
4. Open `https://ran1.app/` on any network. The venue-mode banner should now link to `http://3gpplive.net/` instead of `venue.ran1.app`.

## Final architecture

```text
https://ran1.app       → main secure app (Lovable), shared presence, works everywhere
http://3gpplive.net    → plain-HTTP venue twin (GitHub Pages), meeting-room draft sync
```

## Note about HTTPS on the twin

Never open `https://3gpplive.net/` in a browser. GitHub Pages will serve it and send its own HSTS header, which would pin that browser to HTTPS for a year. Only ever use the explicit `http://` link.