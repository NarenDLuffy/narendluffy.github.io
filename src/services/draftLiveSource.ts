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
import {
  normalizeSegment as norm,
  parseListing,
  walkListing,
  type CrawlResult,
} from "@/lib/listingParser";
import { venueBlockedByScheme } from "@/lib/venueMode";

/**
 * Live draft probe, browser-side.
 *
 * The published drafts.json is produced by GitHub Actions, which can only ever
 * see the public 3GPP tree and only every few minutes. During a meeting week
 * fresher trees exist:
 *
 *   1. the venue server (conventionally http://10.10.10.10/...), fastest but
 *      only reachable from a device on the meeting network AND only readable
 *      when this page itself is served over plain HTTP (mixed content), and
 *   2. the 3GPP sync mirror /ftp/Meetings_3GPP_SYNC/RAN1/Inbox/, which the
 *      venue replicates into well before the archived meeting folder updates.
 *      The browser cannot read it directly (no CORS headers), so it is crawled
 *      through a server function instead.
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

export type LiveDraftOrigin = "venue" | "sync" | "sync-proxy" | "published";

/**
 * Why the venue server is or is not being used. `blocked-mixed-content` is the
 * common case away from venue mode: the browser refuses the request because
 * this page is HTTPS, so it is never even attempted.
 */
export type VenueStatus =
  | "not-checked"
  | "available"
  | "unavailable"
  | "blocked-mixed-content";

export interface LiveDraftReport {
  index: DraftIndex | null;
  origin: LiveDraftOrigin;
  checkedAt: string;
  /** Artifacts that the published index did not know about yet. */
  freshCount: number;
  baseUrl?: string;
  /** Whether the browser could read the venue directory before fallback. */
  venueStatus: VenueStatus;
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

export { parseListing };

/* ---------- crawl ---------- */

async function crawl(rootUrl: string): Promise<CrawlResult | null> {
  return walkListing(rootUrl, fetchText, { maxDepth: MAX_DEPTH, maxRequests: MAX_REQUESTS });
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

type Candidate = {
  origin: LiveDraftOrigin;
  url: string;
  sourceType: DraftSourceType;
  /** "browser" = fetched by this page, "proxy" = crawled by a server function. */
  via: "browser" | "proxy";
};

function candidateBases(): Candidate[] {
  const settings = getLocalSourceSettings();
  // The schedule source has historically used /ftp/RAN/RAN1/Inbox/. That is
  // not the drafts tree. Only accept a configured URL when it explicitly
  // points at the dynamic SYNC drafts Inbox; otherwise use the known drafts
  // root. This matters especially on a new phone with untouched settings.
  const configuredDraftsUrl = settings.baseUrl?.includes("/Meetings_3GPP_SYNC/RAN1/Inbox/")
    ? settings.baseUrl
    : null;
  const venue = configuredDraftsUrl ?? VENUE_DRAFTS_BASE;

  const candidates: Candidate[] = [];
  // Skipped entirely on an HTTPS page: the browser would refuse the request
  // anyway, and attempting it only produces console noise and a wrong
  // "unavailable" verdict.
  if (!venueBlockedByScheme()) {
    candidates.push({
      origin: "venue",
      url: venue.replace(/\/?$/, "/"),
      sourceType: "meeting-local",
      via: "browser",
    });
  }
  // Server-side crawl of the sync mirror — the reliable path, since the
  // browser is refused by CORS on www.3gpp.org.
  candidates.push({
    origin: "sync-proxy",
    url: SYNC_DRAFTS_BASE,
    sourceType: "public",
    via: "proxy",
  });
  // Direct read, last resort: only ever succeeds on a static export where no
  // server function exists and the mirror happens to send CORS headers.
  candidates.push({ origin: "sync", url: SYNC_DRAFTS_BASE, sourceType: "public", via: "browser" });

  return candidates;
}

async function crawlViaProxy(url: string): Promise<CrawlResult | null> {
  try {
    const { crawlSyncDrafts } = await import("@/lib/drafts.functions");
    const result = await crawlSyncDrafts({ data: { url } });
    if (!result?.ok) return null;
    return { folders: result.folders, files: result.files };
  } catch {
    // No server function available (static export) or the crawl failed.
    return null;
  }
}

/**
 * Try the venue server first, then the 3GPP sync mirror (direct, then through
 * the server proxy), and merge whatever answers over the published index.
 * Returns the published index unchanged when nothing is reachable.
 */
export async function probeLiveDrafts(
  meeting: Meeting,
  published: DraftIndex | null,
  agendaCodes: string[] = [],
): Promise<LiveDraftReport> {
  const checkedAt = new Date().toISOString();
  if (typeof window === "undefined") {
    return {
      index: published,
      origin: "published",
      checkedAt,
      freshCount: 0,
      venueStatus: "not-checked",
    };
  }
  const codes = new Set(agendaCodes);
  let venueStatus: VenueStatus = venueBlockedByScheme() ? "blocked-mixed-content" : "not-checked";

  for (const candidate of candidateBases()) {
    const result =
      candidate.via === "proxy" ? await crawlViaProxy(candidate.url) : await crawl(candidate.url);
    if (candidate.origin === "venue") {
      venueStatus = result && result.files.length > 0 ? "available" : "unavailable";
    }
    if (!result || result.files.length === 0) continue;
    const { index, freshCount } = mergeLive(published, result, {
      meetingId: meeting.id,
      sourceType: candidate.sourceType,
      baseUrl: candidate.url,
      agendaCodes: codes,
    });
    return {
      index,
      origin: candidate.origin,
      checkedAt,
      freshCount,
      baseUrl: candidate.url,
      venueStatus,
    };
  }

  return {
    index: published,
    origin: "published",
    checkedAt,
    freshCount: 0,
    venueStatus,
  };
}

export const ORIGIN_LABEL: Record<LiveDraftOrigin, string> = {
  venue: "venue server (10.10.10.10)",
  sync: "3GPP sync mirror",
  "sync-proxy": "3GPP sync mirror (live)",
  published: "published index",
};

