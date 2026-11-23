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
/** Sync trees of every followed working group. */
export const SYNC_ROOT_PREFIXES = [SYNC_ROOT_PREFIX, "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN2/",
  "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN3/",
  "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN/",
  "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN4/",
  "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/SA2/",
];

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

/** Only ever crawl inside the public RAN/RAN1–RAN4 sync trees. */
export function isAllowedSyncUrl(url: string): boolean {
  return !url.includes("..") && SYNC_ROOT_PREFIXES.some((p) => url.startsWith(p));
}

/** One shared scan per tree for every user: reuse a saved result this fresh. */
export const SHARED_FRESH_MS = 90_000;
const LOCK_SECONDS = 60;

type Admin = (typeof import("@/integrations/supabase/client.server"))["supabaseAdmin"];

async function sharedRead(admin: Admin, root: string) {
  const { data } = await admin
    .from("drafts_crawl_cache")
    .select("result, scanned_at")
    .eq("root", root)
    .maybeSingle();
  if (!data?.result || !data.scanned_at) return null;
  return { result: data.result as unknown as CrawlResult, at: Date.parse(data.scanned_at) };
}

/**
 * Crawl one sync tree, shared across all users and server instances: a saved
 * scan younger than SHARED_FRESH_MS is served as-is, and only the caller that
 * wins the database lock actually reads 3GPP — so load stays one scan per
 * ~90 s per tree no matter how many delegates have Drafts open.
 */
export async function crawlSync(url: string): Promise<CrawlResult | null> {
  const root = url.replace(/\/?$/, "/");
  const hit = cache.get(root);
  if (hit && Date.now() - hit.at < CACHE_TTL_MS) return hit.result;

  let admin: Admin | null = null;
  try {
    admin = (await import("@/integrations/supabase/client.server")).supabaseAdmin;
  } catch {
    admin = null;
  }
  if (admin) {
    try {
      const saved = await sharedRead(admin, root);
      if (saved && Date.now() - saved.at < SHARED_FRESH_MS) {
        cache.set(root, { at: saved.at, result: saved.result });
        return saved.result;
      }
      const { data: claimed } = await admin.rpc("claim_drafts_crawl", {
        _root: root,
        _lock_seconds: LOCK_SECONDS,
      });
      if (!claimed) return saved?.result ?? null; // someone else is scanning
    } catch {
      /* shared cache unavailable: fall through to a direct scan */
    }
  }

  const result = await walkListing(root, fetchText, {
    maxDepth: MAX_DEPTH,
    maxRequests: MAX_REQUESTS,
  });
  if (!result) return null;
  cache.set(root, { at: Date.now(), result });
  if (admin) {
    try {
      await admin.from("drafts_crawl_cache").upsert({
        root,
        result: result as never,
        scanned_at: new Date().toISOString(),
        lock_until: new Date(0).toISOString(),
      });
    } catch {
      /* best effort */
    }
  }
  return result;
}
