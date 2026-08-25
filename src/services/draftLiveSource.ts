import type { Meeting } from "@/types/meeting";
import type {
  DraftArtifact,
  DraftArtifactSource,
  DraftEvent,
  DraftFolder,
  DraftIndex,
  DraftSourceType,
} from "@/types/drafts";
import { getLocalSourceSettings } from "./localSource";

/**
 * Live draft probe, browser-side.
 *
 * The published drafts.json is produced by GitHub Actions, which can only ever
 * see the public 3GPP tree and only every few minutes. During a meeting week
 * two fresher trees exist:
 *
 *   1. the venue server (conventionally http://10.10.10.10/...), fastest but
 *      only reachable from the meeting network, and
 *   2. the 3GPP sync mirror /ftp/Meetings_3GPP_SYNC/RAN1/Inbox/, which the
 *      venue replicates into well before the archived meeting folder updates.
 *
 * The same upload therefore appears on up to three servers at three different
 * times. Everything discovered here is merged into the published index by
 * document identity (agenda path + filename), never appended blindly, so one
 * upload stays ONE artifact with several source appearances and one unread
 * mark. Being unreachable is normal and is never an error.
 */

export const VENUE_DRAFTS_BASE = "http://10.10.10.10/ftp/Meetings_3GPP_SYNC/RAN1/Inbox/";
export const SYNC_DRAFTS_BASE = "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN1/Inbox/";

const REQUEST_TIMEOUT_MS = 3500;
// Safety guards only. The Inbox hierarchy is meeting-created and must not be
// truncated at an assumed semantic depth.
const MAX_DEPTH = 20;
const MAX_REQUESTS = 1_000;

export type LiveDraftOrigin = "venue" | "sync" | "published";

export interface LiveDraftReport {
  index: DraftIndex | null;
  origin: LiveDraftOrigin;
  checkedAt: string;
  /** Artifacts that the published index did not know about yet. */
  freshCount: number;
  baseUrl?: string;
}

interface Entry {
  name: string;
  href: string;
  isDir: boolean;
  size?: number;
  modifiedAt?: string;
}

/* ---------- transport ---------- */

async function fetchText(url: string): Promise<string | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const res = await fetch(url, { cache: "no-store", signal: controller.signal });
    if (!res.ok) return null;
    return await res.text();
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

/** Parse an IIS / Apache style directory listing into entries. */
export function parseListing(html: string, baseUrl: string): Entry[] {
  const out: Entry[] = [];
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

    const entry: Entry = { name, href: resolved, isDir };
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
  // files have class="file". The old line parser below matched only a small
  // fraction of these rows because their date and size are in later cells.
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

/* ---------- crawl ---------- */

interface CrawlResult {
  folders: { path: string; name: string; parent: string; depth: number; url: string }[];
  files: { path: string; folderPath: string; name: string; url: string; size?: number; modifiedAt?: string }[];
}

const norm = (s: string) => s.replace(/\s+/g, " ").trim().toLowerCase();

async function crawl(rootUrl: string): Promise<CrawlResult | null> {
  const root = await fetchText(rootUrl);
  if (root === null) return null;

  const result: CrawlResult = { folders: [], files: [] };
  let requests = 1;

  const walk = async (html: string, url: string, path: string, depth: number) => {
    const entries = parseListing(html, url);
    for (const entry of entries) {
      const childPath = path ? `${path}/${norm(entry.name)}` : norm(entry.name);
      if (entry.isDir) {
        result.folders.push({ path: childPath, name: entry.name, parent: path, depth: depth + 1, url: entry.href });
        if (depth + 1 >= MAX_DEPTH || requests >= MAX_REQUESTS) continue;
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

  await walk(root, rootUrl, "", 0);
  return result;
}

/* ---------- semantics (kept deliberately thin) ---------- */

const AGENDA_RE = /(?:^|[^\d])(\d{1,2}(?:\.\d{1,2}){0,4})(?=[^\d]|$)/;

function agendaFromPath(path: string, known: Set<string>): string | null {
  const segments = path.split("/");
  for (let i = segments.length - 1; i >= 0; i -= 1) {
    const match = AGENDA_RE.exec(segments[i] ?? "");
    if (!match) continue;
    let code = match[1];
    while (code) {
      if (known.size === 0 || known.has(code)) return code;
      const cut = code.lastIndexOf(".");
      if (cut < 0) break;
      code = code.slice(0, cut);
    }
  }
  return null;
}

function fileTypeOf(name: string): DraftArtifact["fileType"] {
  const n = name.toLowerCase();
  if (/(fl|moderator|feature\s*lead).*(summary)|summary.*(fl|moderator)/.test(n)) return "fl_summary";
  if (/chair/.test(n)) return "chair_draft";
  if (/\.(docx?|pptx?|xlsx?|zip|pdf|txt)$/.test(n)) return "generic_draft";
  return "unknown";
}

function hash(input: string): string {
  let h = 0;
  for (let i = 0; i < input.length; i += 1) h = (Math.imul(31, h) + input.charCodeAt(i)) | 0;
  return Math.abs(h).toString(36);
}

/* ---------- merge ---------- */

const identity = (folderPath: string, filename: string) => `${folderPath}::${norm(filename)}`;

/**
 * Merge a live crawl over the published index.
 *
 * Merge rules, in order:
 *  - a file already known under the same agenda path + filename is the SAME
 *    artifact: the live server only contributes a source appearance and, if it
 *    is genuinely newer (bigger/newer than what was published), a refreshed
 *    timestamp — no duplicate row, no second notification;
 *  - a file no published or previously live server had is a new artifact plus
 *    exactly one NEW_FILE event;
 *  - published artifacts absent from the live tree are kept untouched: a
 *    server that has not replicated yet is not a deletion.
 */
export function mergeLive(
  published: DraftIndex | null,
  crawlResult: CrawlResult,
  meta: { meetingId: string; sourceType: DraftSourceType; baseUrl: string; agendaCodes: Set<string> },
): { index: DraftIndex; freshCount: number } {
  const now = new Date().toISOString();
  const base: DraftIndex = published
    ? { ...published, folders: [...published.folders], artifacts: [...published.artifacts], events: [...published.events] }
    : {
        schemaVersion: 1,
        meetingId: meta.meetingId,
        generatedAt: now,
        scanState: "ok",
        monitoring: true,
        unmappedFolders: [],
        folders: [],
        artifacts: [],
        events: [],
      };

  const artifactByIdentity = new Map<string, DraftArtifact>();
  base.artifacts.forEach((a) => artifactByIdentity.set(identity(a.folderPath ?? "", a.filename), a));
  const folderByPath = new Map(base.folders.map((f) => [f.normalizedPath, f]));

  crawlResult.folders.forEach((f) => {
    if (folderByPath.has(f.path)) {
      const existing = folderByPath.get(f.path)!;
      existing.lastSeenAt = now;
      return;
    }
    const folder: DraftFolder = {
      id: `lf_${hash(f.path)}`,
      meetingId: meta.meetingId,
      name: f.name,
      normalizedPath: f.path,
      sourceType: meta.sourceType,
      firstSeenAt: now,
      lastSeenAt: now,
      agendaItemId: agendaFromPath(f.path, meta.agendaCodes),
      agendaConfidence: 0.6,
      agendaMethod: "live-path",
      parentPath: f.parent || null,
      depth: f.depth,
      folderType: "generic",
      classificationConfidence: 0.3,
      url: f.url,
      fileCount: 0,
      subtreeFileCount: 0,
    };
    base.folders.push(folder);
    folderByPath.set(f.path, folder);
  });

  const freshEvents: DraftEvent[] = [];

  crawlResult.files.forEach((file) => {
    const key = identity(file.folderPath, file.name);
    const appearance: DraftArtifactSource = {
      sourceType: meta.sourceType,
      sourcePath: file.path,
      url: file.url,
      firstSeenAt: now,
      lastSeenAt: now,
      size: file.size ?? null,
      modifiedAt: file.modifiedAt ?? null,
    };

    const existing = artifactByIdentity.get(key);
    if (existing) {
      // Same document seen on another server: one artifact, no notification.
      const already = existing.sources.find(
        (s) => s.sourceType === appearance.sourceType && s.sourcePath === appearance.sourcePath,
      );
      if (already) {
        already.lastSeenAt = now;
        if (file.size !== undefined) already.size = file.size;
        if (file.modifiedAt) already.modifiedAt = file.modifiedAt;
      } else {
        existing.sources = [...existing.sources, appearance];
      }
      existing.lastSeenAt = now;
      if (file.modifiedAt && (!existing.modifiedAt || file.modifiedAt > existing.modifiedAt)) {
        existing.modifiedAt = file.modifiedAt;
      }
      if (file.size !== undefined && (existing.size ?? 0) < file.size) existing.size = file.size;
      return;
    }

    const folder = folderByPath.get(file.folderPath);
    const artifact: DraftArtifact = {
      id: `la_${hash(key)}`,
      meetingId: meta.meetingId,
      folderId: folder?.id ?? "",
      filename: file.name,
      normalizedPath: file.path,
      fileType: fileTypeOf(file.name),
      classificationConfidence: 0.5,
      documentKey: key,
      firstSeenAt: now,
      lastSeenAt: now,
      agendaItemId: folder?.agendaItemId ?? agendaFromPath(file.path, meta.agendaCodes),
      folderPath: file.folderPath,
      depth: file.path.split("/").length - 1,
      size: file.size ?? null,
      modifiedAt: file.modifiedAt ?? null,
      sources: [appearance],
      revisions: [],
    };
    base.artifacts.push(artifact);
    artifactByIdentity.set(key, artifact);

    freshEvents.push({
      id: `le_${hash(`${key}|${artifact.firstSeenAt}`)}`,
      meetingId: meta.meetingId,
      eventType: "NEW_FILE",
      detectedAt: now,
      sourceType: meta.sourceType,
      agendaItemId: artifact.agendaItemId ?? null,
      artifactId: artifact.id,
      folderId: artifact.folderId,
      title: artifact.filename,
      detail: `Seen on ${meta.sourceType === "meeting-local" ? "venue server" : "3GPP sync"}`,
      fileType: artifact.fileType,
      folderPath: artifact.folderPath ?? null,
      url: file.url,
    });
  });

  // Event identity mirrors artifact identity, so the same upload replicating to
  // a second server never produces a second event.
  const knownEventIds = new Set(base.events.map((e) => e.id));
  const knownTitles = new Set(base.events.map((e) => `${e.folderPath ?? ""}::${norm(e.title)}`));
  const dedupedFresh = freshEvents.filter(
    (e) => !knownEventIds.has(e.id) && !knownTitles.has(`${e.folderPath ?? ""}::${norm(e.title)}`),
  );
  base.events = [...dedupedFresh, ...base.events];
  base.generatedAt = now;
  base.lastSuccessfulScanAt = now;
  base.newEventIds = dedupedFresh.map((e) => e.id);

  return { index: base, freshCount: dedupedFresh.length };
}

/* ---------- probe ---------- */

function candidateBases(): { origin: LiveDraftOrigin; url: string; sourceType: DraftSourceType }[] {
  const settings = getLocalSourceSettings();
  const venue = settings.baseUrl?.includes("10.10.10.10")
    ? settings.baseUrl
    : VENUE_DRAFTS_BASE;
  return [
    { origin: "venue", url: venue.replace(/\/?$/, "/"), sourceType: "meeting-local" },
    { origin: "sync", url: SYNC_DRAFTS_BASE, sourceType: "public" },
  ];
}

/**
 * Try the venue server first, then the 3GPP sync mirror, and merge whatever
 * answers over the published index. Returns the published index unchanged when
 * neither is reachable — the common case off the meeting network.
 */
export async function probeLiveDrafts(
  meeting: Meeting,
  published: DraftIndex | null,
  agendaCodes: string[] = [],
): Promise<LiveDraftReport> {
  const checkedAt = new Date().toISOString();
  if (typeof window === "undefined") {
    return { index: published, origin: "published", checkedAt, freshCount: 0 };
  }
  const codes = new Set(agendaCodes);

  for (const candidate of candidateBases()) {
    const result = await crawl(candidate.url);
    if (!result || result.files.length === 0) continue;
    const { index, freshCount } = mergeLive(published, result, {
      meetingId: meeting.id,
      sourceType: candidate.sourceType,
      baseUrl: candidate.url,
      agendaCodes: codes,
    });
    return { index, origin: candidate.origin, checkedAt, freshCount, baseUrl: candidate.url };
  }

  return { index: published, origin: "published", checkedAt, freshCount: 0 };
}

export const ORIGIN_LABEL: Record<LiveDraftOrigin, string> = {
  venue: "venue server (10.10.10.10)",
  sync: "3GPP sync mirror",
  published: "published index",
};
