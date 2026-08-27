# Restore the full RAN1 Live venue twin on 3gpplive.net

## Confirmed diagnosis

- `http://3gpplive.net/` currently returns a GitHub/Jekyll page generated from the repository README, not the compiled RAN1 Live application. That is why it only presents project information and a “How to use this website” link.
- The repository already contains a GitHub Actions Pages workflow that builds the React application and writes `3gpplive.net` into the deployed artifact's `CNAME`, but the live response shows GitHub Pages is serving the repository source instead of that artifact.
- The domain's HTTP endpoint currently responds directly with `200 OK`; it does not issue an HTTP-to-HTTPS redirect at the server. A device that changes the navigation to HTTPS is therefore applying remembered HTTPS/HSTS or browser HTTPS-first behavior locally.

## What will change

1. **Make the Pages artifact unambiguous**
   - Tighten the deployment workflow so it locates and validates the actual static app output before upload.
   - Fail deployment if the output is missing the app's generated HTML/assets, rather than allowing a misleading README/Jekyll site to remain unnoticed.
   - Keep the custom-domain `CNAME` and `.nojekyll` inside that exact artifact.

2. **Keep venue navigation explicitly on HTTP**
   - Retain `3gpplive.net` as requested.
   - Preserve the full current route when moving from `ran1.app` to the twin, while keeping the small allow-listed preference transfer.
   - Detect an HTTPS-loaded twin and provide a clear return/retry path instead of leaving the user on a documentation-like or unusable page.

3. **Correct the GitHub Pages source setting**
   - In GitHub, set **Settings → Pages → Build and deployment → Source** to **GitHub Actions**, then manually run **Deploy to GitHub Pages** once.
   - Confirm the workflow's deployment environment reports `3gpplive.net` and that the uploaded artifact—not the repository branch—is serving the domain.

4. **Recover affected phones/browsers**
   - Because the server itself is not redirecting HTTP, clear stored website/security data for `3gpplive.net` on devices that still force HTTPS, then enter through `https://ran1.app` rather than typing the twin address.
   - This is a one-time device step while retaining the same hostname; code cannot clear a browser's remembered HTTPS policy.

## Verification

- Request `http://3gpplive.net/` and verify it returns the generated RAN1 Live HTML and JavaScript assets, not Jekyll markup or README content.
- Open `/schedule`, `/drafts`, and another deep route directly over HTTP and confirm the shared RAN1 Live layout renders on each.
- Start at `https://ran1.app`, use venue mode, and confirm the destination remains `http://3gpplive.net/...` on a clean browser profile.
- On meeting Wi-Fi, use **Refresh now** in Drafts and confirm the source reports the venue server when `10.10.10.10` is reachable.

## Important limitation

Keeping `3gpplive.net` means devices that have already remembered HTTPS for that hostname may require their stored site/security data to be cleared. If a browser's HTTPS-only policy cannot be disabled for this domain, a fresh hostname would be the only reliable fallback, but that is outside this chosen plan.
