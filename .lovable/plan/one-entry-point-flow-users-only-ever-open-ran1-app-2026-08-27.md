# One-entry-point flow: users only ever open ran1.app

## Goal

Delegates only ever open `https://ran1.app`. When they are at a meeting, the app itself offers (or automatically performs) the hop to the plain-HTTP venue twin at `http://3gpplive.net` so drafts can be read from `http://10.10.10.10/`. Nobody needs to know or type the twin's address.

## How the user experience works (already built)

1. User opens `https://ran1.app` on any network.
2. If a meeting is active and the page is on HTTPS, the app shows the venue banner: "At the meeting? Open venue mode."
3. **Open venue mode** → one tap, hops to `http://3gpplive.net` carrying bookmarks, follows and read state.
4. **Always at venues** → future visits to `ran1.app` during an active meeting switch automatically, zero taps.
5. In venue mode, a banner offers **Back to ran1.app** for check-ins and account-based features.

No code changes are required for this flow — `src/lib/venueMode.ts` and `VenueModeBanner.tsx` already implement it. What remains is finishing the twin's deployment so the hop target actually exists.

## Remaining manual steps (one time, by you)

### 1. DNS at the 3gpplive.net registrar

Point the apex domain at GitHub Pages:

| Type | Name | Value           |
| ---- | ---- | --------------- |
| A    | @    | 185.199.108.153 |
| A    | @    | 185.199.109.153 |
| A    | @    | 185.199.110.153 |
| A    | @    | 185.199.111.153 |

Verify with `nslookup 3gpplive.net` — the four GitHub IPs should appear.

### 2. GitHub Pages custom domain

1. Repo `https://github.com/narendluffy/narendluffy.github.io` → **Settings → Pages → Custom domain**.
2. Enter `3gpplive.net`, Save.
3. **Uncheck "Enforce HTTPS"** (required — the twin must stay plain HTTP).
4. Wait for DNS verification.

### 3. Set the VENUE_HOST repository variable

**Settings → Secrets and variables → Actions → Variables → New repository variable**: name `VENUE_HOST`, value `3gpplive.net`.

### 4. Re-run the deploy workflow

**Actions → Deploy to GitHub Pages → Run workflow.**

### 5. Clean up the old venue.ran1.app records

1. Remove `venue.ran1.app` from the repo's Pages custom-domain field if still present.
2. In Lovable: **Project Settings → Domains → ran1.app → ⋯ → Configure → Manage DNS records** → delete the `venue` CNAME.

`ran1.app` and `www.ran1.app` stay untouched — they are the single entry point.

## Verification

1. Open `https://ran1.app` during an active meeting → the venue banner appears and links to `http://3gpplive.net`.
2. Tap **Open venue mode** on meeting Wi-Fi → the same app loads over plain HTTP; **Drafts → Refresh now** reads `10.10.10.10`.
3. Tap **Always at venues**, reload `ran1.app` → it hops automatically.
4. `https://ran1.app` presence/check-ins still work on the secure site.

## Final architecture

```text
https://ran1.app      → the ONLY address users open; secure app, shared presence
http://3gpplive.net   → plain-HTTP venue twin, reached only via the banner/auto-switch
```

## Warning

Never open `https://3gpplive.net/` in a browser — GitHub would pin that browser to HTTPS for a year via HSTS. The app only ever navigates to the explicit `http://` address, so users are safe as long as they go through `ran1.app`.
