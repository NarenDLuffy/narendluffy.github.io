/**
 * All generated data lives under public/data and is served relative to the
 * deployment base (GitHub Pages may host the app under a sub-path).
 */
export function dataUrl(path: string): string {
  const base = import.meta.env.BASE_URL || "/";
  return `${base.endsWith("/") ? base : `${base}/`}data/${path}`;
}
