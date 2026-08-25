# Publish RAN1 Live to ran1.app for colleague feedback

## Goal
Make the app publicly available at the configured custom domain `ran1.app` so colleagues can try it, with a clear path to unpublish later. Keep the GitHub Pages/free `github.io` option ready as a follow-up.

## Current state
- The app is **not yet published** through Lovable (`is_published: false`).
- Effective publish visibility is already **public**, so once published anyone with the link can view it.
- The custom domains `https://ran1.app` and `https://www.ran1.app` are configured.
- The codebase is currently only in Lovable private storage; it is **not synced to GitHub** yet.

## Plan

1. **Publish to Lovable**
   - Trigger a Lovable publish so the app goes live.
   - The deployment should appear at the configured custom domain `https://ran1.app`.

2. **Verify live deployment**
   - Confirm the site loads at `https://ran1.app`.
   - Smoke-test key routes (schedule, drafts, help) and check that no sensitive/company-presence data is exposed.

3. **Share with colleagues**
   - Provide the public URL and a short feature checklist they can try.

4. **Document how to unpublish later**
   - Explain where to find the Unpublish control in Lovable so the user can take the site down after collecting feedback.

5. **Follow-up: GitHub sync (optional, after feedback)**
   - Connect the project to `github.com/NarenDLuffy/ran1-live` from the Lovable editor.
   - Enable GitHub Pages so the free `https://NarenDLuffy.github.io/ran1-live/` URL works as a long-term fallback after the `ran1.app` domain renewal.

## What the user needs to do
- Nothing technical for step 1; the agent can trigger the publish.
- For step 5, the user must authorize the Lovable GitHub App and create/select the repo from the Lovable UI.
