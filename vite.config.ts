// @lovable.dev/vite-tanstack-config already includes the following — do NOT add them manually
// or the app will break with duplicate plugins:
//   - TanStack devtools (dev-only, first), tanstackStart, viteReact, tailwindcss, tsConfigPaths,
//     nitro (build-only using cloudflare as a default target), VITE_* env injection, @ path alias,
//     React/TanStack dedupe, error logger plugins, and sandbox detection (port/host/strictPort).
// You can pass additional config via defineConfig({ vite: { ... }, etc... }) if needed.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

// GitHub Pages project sites are served from /<repo>/. Set BASE_PATH in the
// Pages workflow for that case; leave it unset for a custom domain.
const base = process.env["BASE_PATH"] || "/";

// Static export mode is used by the GitHub Pages workflow. It disables the
// Nitro server bundle so TanStack Start emits prerendered HTML for static hosts.
const staticExport = process.env["STATIC_EXPORT"] === "1";

export default defineConfig({
  vite: { base },
  tanstackStart: {
    // Redirect TanStack Start's bundled server entry to src/server.ts (our SSR error wrapper).
    // nitro/vite builds from this
    server: { entry: "server" },
    // Static prerender for GitHub Pages: emit real HTML for every static route.
    prerender: {
      enabled: true,
      crawlLinks: true,
      failOnError: false,
    },
  },
  // Outside the Lovable sandbox (e.g. GitHub Actions) we either disable Nitro
  // for a fully static export, or keep it for deploy targets that need a server.
  // The sandbox ignores this option and keeps its own Cloudflare target.
  nitro: staticExport ? false : {
    preset: "static",
    output: {
      dir: "dist",
      publicDir: "dist/client",
    },
  },
});
