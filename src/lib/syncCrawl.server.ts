import { walkListing, type CrawlResult } from "./listingParser";

/**
 * Server-side crawl of the public 3GPP sync mirror.
 *
 * The browser cannot read these listings directly: www.3gpp.org sends no CORS
 * headers, so every in-page fetch fails regardless of network. Doing the walk
 * server-side removes that limitation entirely — this is the path that keeps
 * the published app live when the user is NOT on the meeting network.
 *
 * It deliberately cannot help with the venue server (10.10.10.10): that address
 * only exists inside the meeting-room LAN, so a datacenter worker has no route
 * to it. Venue access stays a browser-side job.
 */

export const SYNC_ROOT_PREFIX = "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN1/";

const REQUEST_TIMEOUT_MS = 8_000;
const MAX_DEPTH = 12;
const MAX_REQUESTS = 240;
const CACHE_TTL_MS = 30_000;

interface CacheEntry {
  at: number;
  result: CrawlResult;
}

// Module-scope map is fine: it is only a best-effort per-isolate cache and is
// never relied on for correctness.
const cache = new Map<string, CacheEntry>();

async function fetchText(url: string): Promise<string | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      redirect: "follow",
      signal: controller.signal,
      headers: { accept: "text/html,*/*" },
    });
    if (!res.ok) return null;
    return await res.text();
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

/** Only ever crawl inside the public RAN1 sync tree. */
export function isAllowedSyncUrl(url: string): boolean {
  return url.startsWith(SYNC_ROOT_PREFIX);
}

export async function crawlSync(url: string): Promise<CrawlResult | null> {
  const root = url.replace(/\/?$/, "/");
  const hit = cache.get(root);
  if (hit && Date.now() - hit.at < CACHE_TTL_MS) return hit.result;

  const result = await walkListing(root, fetchText, {
    maxDepth: MAX_DEPTH,
    maxRequests: MAX_REQUESTS,
  });
  if (!result) return null;
  cache.set(root, { at: Date.now(), result });
  return result;
}
