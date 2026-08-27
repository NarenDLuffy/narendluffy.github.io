# Fix the 3gpplive.net venue-twin domain (DNS, not code)

## What the error actually means

GitHub Pages says `www.3gpplive.net is improperly configured — Domain's DNS record could not be retrieved (InvalidDNSError)`.

Live DNS check just now:

```text
3gpplive.net        A     172.67.151.184, 104.21.1.8   (Cloudflare proxy IPs)
www.3gpplive.net    —     no record at all
nameservers         ursula/eric.ns.cloudflare.com      (Cloudflare DNS)
```

Two separate problems:

1. `www.3gpplive.net` has **no DNS record**, so GitHub cannot verify it. That is the exact error in the screenshot.
2. The apex `3gpplive.net` does not point at GitHub Pages either — it resolves to Cloudflare's proxy IPs. Even after the record is fixed, a **proxied (orange-cloud)** record breaks venue mode, because Cloudflare terminates TLS and typically forces HTTPS. The whole point of this twin is that it must answer on plain **HTTP**.

So no code change fixes this; the records at Cloudflare have to change.

## What to change at Cloudflare (you do this, in the Cloudflare dashboard)

DNS tab for `3gpplive.net`:

- Delete the two existing proxied A records on `@`.
- Add four A records on `@`, all with the proxy **off (grey cloud, "DNS only")**:
  - `185.199.108.153`
  - `185.199.109.153`
  - `185.199.110.153`
  - `185.199.111.153`
- Add `www` as a CNAME to `<your-github-username>.github.io`, also **DNS only**.

SSL/TLS → Edge Certificates for this zone:

- Turn **Always Use HTTPS** off.
- Turn **Automatic HTTPS Rewrites** off.
- Make sure no Page Rule / Redirect Rule forces HTTPS.

(With the grey cloud these settings mostly stop applying anyway, but leaving them on is a trap if the proxy is ever re-enabled.)

## What to change in GitHub

- **Settings → Pages → Custom domain**: set it to `3gpplive.net` (the apex), not `www`. The deploy workflow already writes `3gpplive.net` into the build artifact's `CNAME`, so these must match or Pages will keep flip-flopping.
- **Settings → Pages → Enforce HTTPS**: leave it **unchecked**. Checking it makes GitHub send HSTS and permanently kills the plain-HTTP twin on this domain.
- **Settings → Pages → Source**: must be **GitHub Actions**.
- Re-run the **Deploy to GitHub Pages** workflow after DNS propagates.

## Optional code touch-up

If you want `www.3gpplive.net` to work as well as the apex, that is only the CNAME above — the app itself needs no change; `VENUE_HOST` stays `3gpplive.net`. If you would rather not maintain `www` at all, skip the `www` CNAME and simply clear the `www` entry from the GitHub Pages custom-domain field, and the error disappears.

## How we will verify

Once the records are in, checks that must pass before venue mode works:

1. `3gpplive.net` resolves to the four `185.199.x.153` addresses (no Cloudflare IPs).
2. `http://3gpplive.net/` returns HTTP 200 and serves the compiled app — not a redirect to `https://`, and not the README/Jekyll page.
3. Opening `https://ran1.app` at the meeting hops to `http://3gpplive.net/...` and the Drafts page can read `10.10.10.10`.

Tell me when the Cloudflare records are updated and I will re-run these checks from here.
