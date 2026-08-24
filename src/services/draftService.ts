import { queryOptions } from "@tanstack/react-query";
import { dataUrl } from "@/lib/dataUrl";
import { probeLiveDrafts, type LiveDraftOrigin } from "./draftLiveSource";
import type { Meeting } from "@/types/meeting";
import type {
  AgendaActivity,
  DraftArtifact,
  DraftEvent,
  DraftFolder,
  DraftIndex,
} from "@/types/drafts";

/**
 * Read boundary for the draft / FL summary tracker.
 *
 * Deliberately separate from scheduleService: draft scanning runs on its own
 * cadence and must never delay or break the timetable. Both sides agree only
 * on agenda item codes.
 */

const cacheKey = (slug: string) => `ran1live.drafts.v1.${slug}`;

export const EVENT_LABEL: Record<DraftEvent["eventType"], string> = {
  NEW_FILE: "New file",
  FILE_UPDATED: "Updated",
  NEW_FOLDER: "New folder",
  FILE_REMOVED: "Removed",
  FOLDER_REMOVED: "Folder removed",
};

const SEMANTIC_LABEL: Record<string, string> = {
  NEW_ROUND: "New round",
  NEW_FL_FOLDER: "FL folder",
  FL_SUMMARY_UPDATED: "FL summary",
};

/**
 * Show the semantic label when the scanner was confident, the plain
 * filesystem fact otherwise. A folder is never called a round on a guess.
 */
export function eventLabel(event: DraftEvent): string {
  return (
    (event.semanticType ? SEMANTIC_LABEL[event.semanticType] : undefined) ??
    EVENT_LABEL[event.eventType]
  );
}

export interface DraftResult {
  index: DraftIndex | null;
  stale: boolean;
  error?: string;
  /** Which server actually answered on the last live probe. */
  liveOrigin?: LiveDraftOrigin;
  liveCheckedAt?: string;
  /** Files the live probe found that the published index did not have. */
  freshCount?: number;
}

function readCache(slug: string): DraftIndex | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(cacheKey(slug));
    return raw ? (JSON.parse(raw) as DraftIndex) : null;
  } catch {
    return null;
  }
}

export async function loadDrafts(meeting: Meeting): Promise<DraftResult> {
  const slug = meeting.slug;
  try {
    const res = await fetch(dataUrl(`meetings/${slug}/drafts.json`), { cache: "no-store" });
    if (res.status === 404) return { index: null, stale: false };
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const index = (await res.json()) as DraftIndex;
    if (typeof window !== "undefined") {
      try {
        window.localStorage.setItem(cacheKey(slug), JSON.stringify(index));
      } catch {
        /* quota */
      }
    }
    return { index, stale: false };
  } catch (err) {
    const cached = readCache(slug);
    return {
      index: cached,
      stale: Boolean(cached),
      error: err instanceof Error ? err.message : "draft index unavailable",
    };
  }
}

/**
 * Published index first, then a live probe of the venue server and the 3GPP
 * sync mirror. The live crawl is merged over the published index by document
 * identity, so a file replicated to a second server later in the day stays one
 * artifact with one unread mark.
 */
export async function loadDraftsLive(meeting: Meeting): Promise<DraftResult> {
  const published = await loadDrafts(meeting);
  try {
    const live = await probeLiveDrafts(meeting, published.index);
    if (live.origin === "published") return published;
    return {
      ...published,
      index: live.index,
      liveOrigin: live.origin,
      liveCheckedAt: live.checkedAt,
      freshCount: live.freshCount,
    };
  } catch {
    return published;
  }
}

export function draftsQueryOptions(meeting?: Meeting) {
  return queryOptions({
    queryKey: ["drafts", meeting?.slug ?? "none"],
    queryFn: () =>
      meeting ? loadDraftsLive(meeting) : Promise.resolve({ index: null, stale: false }),
    enabled: Boolean(meeting),
    // Draft folders churn constantly during a session: check often, and keep
    // checking while the tab is in the background.
    staleTime: 20_000,
    refetchInterval: 60_000,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
  });
}

/* ---------- derivations ---------- */

export function foldersById(index: DraftIndex): Map<string, DraftFolder> {
  return new Map(index.folders.map((f) => [f.id, f]));
}

export function artifactsById(index: DraftIndex): Map<string, DraftArtifact> {
  return new Map(index.artifacts.map((a) => [a.id, a]));
}

export function artifactsForAgenda(index: DraftIndex, code: string): DraftArtifact[] {
  return index.artifacts
    .filter((a) => a.agendaItemId === code && !a.removedAt)
    .sort((a, b) => (b.modifiedAt ?? b.lastSeenAt).localeCompare(a.modifiedAt ?? a.lastSeenAt));
}

/** Files the scanner could not attach to any agenda item — kept, never guessed. */
export function unmappedArtifacts(index: DraftIndex): DraftArtifact[] {
  return index.artifacts
    .filter((a) => !a.agendaItemId && !a.removedAt)
    .sort((a, b) => (b.modifiedAt ?? b.lastSeenAt).localeCompare(a.modifiedAt ?? a.lastSeenAt));
}

/**
 * Newest-first ordering for two revisions of the same document.
 *
 * The same filename genuinely repeats across folders (Round 1 and Round 2 both
 * hold `FL_summary_v01.docx`), so recency is decided by folder depth-agnostic
 * signals in order: explicit version number, server timestamp, first sighting.
 */
export function compareRecency(a: DraftArtifact, b: DraftArtifact): number {
  const ra = a.revision ?? -1;
  const rb = b.revision ?? -1;
  const ta = a.modifiedAt ?? a.lastSeenAt ?? "";
  const tb = b.modifiedAt ?? b.lastSeenAt ?? "";
  if (ta !== tb) return tb.localeCompare(ta);
  if (ra !== rb) return rb - ra;
  return (b.firstSeenAt ?? "").localeCompare(a.firstSeenAt ?? "");
}

/** Latest FL summary anywhere in the agenda item's subtree (§19). */
export function latestFlSummary(
  index: DraftIndex,
  code: string,
): DraftArtifact | undefined {
  return index.artifacts
    .filter((a) => a.agendaItemId === code && a.fileType === "fl_summary" && !a.removedAt)
    .sort(compareRecency)[0];
}

/* ---------- generic directory tree ---------- */

export interface DraftTreeNode {
  folder: DraftFolder;
  /** Path segments from the agenda folder down to this folder. */
  breadcrumbs: string[];
  files: DraftArtifact[];
  children: DraftTreeNode[];
  subtreeFileCount: number;
}

/**
 * Rebuild whatever hierarchy the scanner discovered under an agenda item.
 *
 * The UI renders this tree as-is: no level is invented when a meeting puts its
 * files straight into the agenda folder, and no level is dropped when a
 * moderator nests four folders deep.
 */
export function buildDraftTree(index: DraftIndex, code: string): DraftTreeNode[] {
  const folders = index.folders.filter((f) => f.agendaItemId === code && !f.removedAt);
  if (folders.length === 0) return [];

  const byPath = new Map(folders.map((f) => [f.normalizedPath, f]));
  const filesByFolder = new Map<string, DraftArtifact[]>();
  index.artifacts
    .filter((a) => a.agendaItemId === code && !a.removedAt)
    .forEach((a) => {
      const key = a.folderPath ?? "";
      const list = filesByFolder.get(key) ?? [];
      list.push(a);
      filesByFolder.set(key, list);
    });

  const nodes = new Map<string, DraftTreeNode>();
  folders.forEach((folder) => {
    nodes.set(folder.normalizedPath, {
      folder,
      breadcrumbs: [],
      files: (filesByFolder.get(folder.normalizedPath) ?? []).sort(compareRecency),
      children: [],
      subtreeFileCount: 0,
    });
  });

  const roots: DraftTreeNode[] = [];
  nodes.forEach((node, path) => {
    const parentPath = node.folder.parentPath ?? "";
    const parent = parentPath && byPath.has(parentPath) ? nodes.get(parentPath) : undefined;
    if (parent && parent !== node) parent.children.push(node);
    else roots.push(node);
    void path;
  });

  const finish = (node: DraftTreeNode, trail: string[]): number => {
    node.breadcrumbs = [...trail, node.folder.name];
    node.children.sort((a, b) => a.folder.name.localeCompare(b.folder.name));
    let total = node.files.length;
    node.children.forEach((child) => {
      total += finish(child, node.breadcrumbs);
    });
    node.subtreeFileCount = total;
    return total;
  };
  roots.sort((a, b) => a.folder.normalizedPath.localeCompare(b.folder.normalizedPath));
  roots.forEach((root) => finish(root, []));
  return roots;
}

/**
 * Roll events up per agenda item. `seenAt` (per code) decides what is unread,
 * `since` suppresses history from before the user started following.
 */
function emptyActivity(code: string, latestFl?: DraftArtifact): AgendaActivity {
  return {
    agendaItemId: code,
    events: [],
    unread: [],
    unreadCount: 0,
    flUpdates: 0,
    newFiles: 0,
    newRounds: 0,
    newFolders: 0,
    fileCount: 0,
    flCount: 0,
    ...(latestFl ? { latestFlSummary: latestFl } : {}),
  };
}

export function buildActivity(
  index: DraftIndex | null,
  opts: {
    seenAt?: (code: string) => string | undefined;
    since?: (code: string) => string | undefined;
  } = {},
): Map<string, AgendaActivity> {
  const out = new Map<string, AgendaActivity>();
  if (!index) return out;

  // Latest FL summary is searched across the whole agenda subtree, wherever a
  // moderator happened to file it (§19), and duplicated filenames across
  // rounds resolve to the genuinely newest revision.
  const latestFl = new Map<string, DraftArtifact>();
  index.artifacts.forEach((a) => {
    if (a.fileType !== "fl_summary" || !a.agendaItemId || a.removedAt) return;
    const current = latestFl.get(a.agendaItemId);
    if (!current || compareRecency(a, current) < 0) latestFl.set(a.agendaItemId, a);
  });

  // Seed one entry per agenda item that has files, so the tracker is browsable
  // even before (or without) any change events — a fresh baseline scan has no
  // events but plenty of drafts.
  index.artifacts.forEach((a) => {
    const code = a.agendaItemId ?? "unmapped";
    if (a.removedAt) return;
    const entry = out.get(code) ?? emptyActivity(code, latestFl.get(code));
    entry.fileCount += 1;
    if (a.fileType === "fl_summary") entry.flCount += 1;
    const stamp = a.modifiedAt ?? a.lastSeenAt;
    if (stamp && (!entry.latestFileAt || stamp > entry.latestFileAt)) entry.latestFileAt = stamp;
    out.set(code, entry);
  });

  index.events.forEach((e) => {
    const code = e.agendaItemId ?? "unmapped";
    const entry = out.get(code) ?? emptyActivity(code, latestFl.get(code));

    entry.events.push(e);
    if (e.semanticType === "FL_SUMMARY_UPDATED") entry.flUpdates += 1;
    if (e.eventType === "NEW_FILE") entry.newFiles += 1;
    if (e.eventType === "NEW_FOLDER") {
      entry.newFolders += 1;
      if (e.semanticType === "NEW_ROUND") entry.newRounds += 1;
    }

    const seen = opts.seenAt?.(code);
    const since = opts.since?.(code);
    const isUnread = (!seen || e.detectedAt > seen) && (!since || e.detectedAt >= since);
    if (isUnread) {
      entry.unread.push(e);
      entry.unreadCount = entry.unread.length;
    }
    if (!entry.latestAt || e.detectedAt > entry.latestAt) entry.latestAt = e.detectedAt;
    out.set(code, entry);
  });

  out.forEach((entry) => {
    entry.events.sort((a, b) => b.detectedAt.localeCompare(a.detectedAt));
    entry.unread.sort((a, b) => b.detectedAt.localeCompare(a.detectedAt));
  });
  return out;
}

export function formatSize(bytes?: number | null): string {
  if (!bytes || bytes <= 0) return "";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i += 1;
  }
  return `${value >= 10 || i === 0 ? Math.round(value) : value.toFixed(1)} ${units[i]}`;
}

export function relativeTime(iso?: string | null, now = Date.now()): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const mins = Math.round((now - then) / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}
