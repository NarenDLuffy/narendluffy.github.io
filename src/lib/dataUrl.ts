/**
 * All generated data lives under public/data. The background jobs commit fresh
 * copies to the GitHub repo every few minutes, so the app reads that live copy
 * first and only falls back to the copy bundled at publish time. This keeps
 * the schedule and drafts current without re-publishing.
 */
const LIVE_DATA_BASE =
  (import.meta.env.VITE_LIVE_DATA_BASE as string | undefined) ??
  "https://raw.githubusercontent.com/NarenDLuffy/narendluffy.github.io/main/public/data/";

export function dataUrl(path: string): string {
  const base = import.meta.env.BASE_URL || "/";
  return `${base.endsWith("/") ? base : `${base}/`}data/${path}`;
}

export function liveDataUrl(path: string): string {
  const base = LIVE_DATA_BASE.endsWith("/") ? LIVE_DATA_BASE : `${LIVE_DATA_BASE}/`;
  return `${base}${path}?t=${Date.now()}`;
}

/** Fetch generated data: live repo copy first, bundled copy as fallback. */
export async function fetchData(path: string): Promise<Response> {
  if (LIVE_DATA_BASE) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 8000);
      const res = await fetch(liveDataUrl(path), { cache: "no-store", signal: controller.signal });
      clearTimeout(timer);
      if (res.ok || res.status === 404) return res;
    } catch {
      /* offline or blocked: fall back to the bundled copy */
    }
  }
  return fetch(dataUrl(path), { cache: "no-store" });
}
