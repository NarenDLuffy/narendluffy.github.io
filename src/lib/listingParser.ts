/**
 * Shared parser for IIS / Apache style directory listings.
 *
 * Lives in its own browser-safe module because two very different callers need
 * it: the in-browser venue crawl (`draftLiveSource`) and the server-side sync
 * crawl (`syncCrawl.server`). Keeping one implementation means a listing quirk
 * only ever has to be fixed once.
 */

export interface ListingEntry {
  name: string;
  href: string;
  isDir: boolean;
  size?: number;
  modifiedAt?: string;
}

export function parseListing(html: string, baseUrl: string): ListingEntry[] {
  const out: ListingEntry[] = [];
  const seen = new Set<string>();

  const decode = (value: string) =>
    value
      .replace(/&amp;/gi, "&")
      .replace(/&quot;/gi, '"')
      .replace(/&#39;|&apos;/gi, "'")
      .replace(/&lt;/gi, "<")
      .replace(/&gt;/gi, ">");

  const add = (
    hrefValue: string,
    labelValue: string,
    isDir: boolean,
    stamp?: string,
    sizeValue?: string,
  ) => {
    const href = decode(hrefValue.trim());
    const name = decode(labelValue.replace(/<[^>]*>/g, "").trim()).replace(/\/$/, "");
    if (!href || !name || name === ".." || /parent directory/i.test(name)) return;
    if (href.startsWith("?") || href.startsWith("#") || seen.has(href)) return;
    let resolved: string;
    try {
      resolved = new URL(href, baseUrl).toString();
    } catch {
      return;
    }
    // Ignore breadcrumb/navigation links outside the directory being crawled.
    const root = baseUrl.replace(/\/?$/, "/");
    if (!resolved.startsWith(root)) return;
    seen.add(href);

    const entry: ListingEntry = { name, href: resolved, isDir };
    const sizeText = sizeValue?.replace(/[^\d]/g, "") ?? "";
    if (sizeText) entry.size = Number(sizeText);
    const normalizedStamp = stamp?.trim().replace(
      /^(\d{4})\/(\d{2})\/(\d{2})\s+(\d{2}:\d{2}(?::\d{2})?)$/,
      "$1-$2-$3T$4Z",
    );
    const parsed = normalizedStamp ? new Date(normalizedStamp) : null;
    if (parsed && !Number.isNaN(parsed.getTime())) entry.modifiedAt = parsed.toISOString();
    out.push(entry);
  };

  // Current 3GPP listings are HTML tables. Folder rows have a plain anchor;
  // files have class="file", with date and size in later cells.
  const rowRe = /<tr\b[^>]*>([\s\S]*?)<\/tr>/gi;
  let rowMatch: RegExpExecArray | null;
  while ((rowMatch = rowRe.exec(html))) {
    const row = rowMatch[1] ?? "";
    const anchor = /<a\b([^>]*)href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/i.exec(row);
    if (!anchor) continue;
    const attrs = anchor[1] ?? "";
    const cells = [...row.matchAll(/<td\b[^>]*>([\s\S]*?)<\/td>/gi)].map((match) =>
      decode((match[1] ?? "").replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim()),
    );
    const isFile = /\bclass\s*=\s*["'][^"']*\bfile\b/i.test(attrs);
    const stamp = cells.find((cell) => /\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2}/.test(cell));
    const size = cells.find((cell) => /^\s*[\d,.]+\s*(?:bytes?|kb|mb|gb)?\s*$/i.test(cell));
    add(anchor[2] ?? "", anchor[3] ?? "", !isFile, stamp, size);
  }

  if (out.length > 0) return out;

  // IIS listings: "<date> <time>  <dir|size> <a href="...">name</a>"
  const lineRe =
    /(\d{1,2}\/\d{1,2}\/\d{2,4}\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)?[^<]*?(&lt;dir&gt;|<dir>|[\d,]+)?\s*<a\s+href="([^"]+)"[^>]*>([^<]+)<\/a>/gi;

  let m: RegExpExecArray | null;
  while ((m = lineRe.exec(html))) {
    const stamp = m[1];
    const marker = m[2];
    const href = m[3] ?? "";
    const name = (m[4] ?? "").trim();
    const isDir = Boolean(marker && /dir/i.test(marker)) || href.endsWith("/") || !name.includes(".");
    add(href, name, isDir, stamp, marker && !/dir/i.test(marker) ? marker : undefined);
  }
  return out;
}

/** Result of walking a listing tree, shared by the browser and server crawlers. */
export interface CrawlResult {
  folders: { path: string; name: string; parent: string; depth: number; url: string }[];
  files: {
    path: string;
    folderPath: string;
    name: string;
    url: string;
    size?: number;
    modifiedAt?: string;
  }[];
}

export const normalizeSegment = (s: string) => s.replace(/\s+/g, " ").trim().toLowerCase();

/**
 * Walk a directory listing tree using a caller-supplied fetcher.
 *
 * The Inbox hierarchy is meeting-created, so depth is only bounded as a safety
 * guard — never truncated at an assumed semantic level.
 */
export async function walkListing(
  rootUrl: string,
  fetchText: (url: string) => Promise<string | null>,
  limits: { maxDepth: number; maxRequests: number },
): Promise<CrawlResult | null> {
  const rootHtml = await fetchText(rootUrl);
  if (rootHtml === null) return null;

  const result: CrawlResult = { folders: [], files: [] };
  let requests = 1;

  const walk = async (html: string, url: string, path: string, depth: number) => {
    for (const entry of parseListing(html, url)) {
      const childPath = path
        ? `${path}/${normalizeSegment(entry.name)}`
        : normalizeSegment(entry.name);
      if (entry.isDir) {
        result.folders.push({
          path: childPath,
          name: entry.name,
          parent: path,
          depth: depth + 1,
          url: entry.href,
        });
        if (depth + 1 >= limits.maxDepth || requests >= limits.maxRequests) continue;
        requests += 1;
        const childHtml = await fetchText(entry.href);
        if (childHtml) await walk(childHtml, entry.href, childPath, depth + 1);
      } else {
        const file: CrawlResult["files"][number] = {
          path: childPath,
          folderPath: path,
          name: entry.name,
          url: entry.href,
        };
        if (entry.size !== undefined) file.size = entry.size;
        if (entry.modifiedAt) file.modifiedAt = entry.modifiedAt;
        result.files.push(file);
      }
    }
  };

  await walk(rootHtml, rootUrl, "", 0);
  return result;
}
