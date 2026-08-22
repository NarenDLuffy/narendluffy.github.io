/**
 * Draft tracker model — mirror of `draft_tracker/models.py`.
 *
 * Published per meeting as public/data/meetings/<slug>/drafts.json by the
 * draft-watch workflow. A logical artifact is modelled separately from its
 * source appearances, so a file seen first on the meeting-local server and
 * later on the public 3GPP site stays one artifact with one notification.
 */

export type DraftSourceType = "public" | "meeting-local";

/** Filesystem facts only — never RAN1 vocabulary. */
export type DraftEventType =
  | "NEW_FILE"
  | "FILE_UPDATED"
  | "NEW_FOLDER"
  | "FILE_REMOVED"
  | "FOLDER_REMOVED";

/** Optional interpretation layered on a fact, present only when confident. */
export type DraftSemanticType =
  | "NEW_ROUND"
  | "NEW_FL_FOLDER"
  | "FL_SUMMARY_UPDATED"
  | "OTHER";

/**
 * A discovered folder is generic until proven otherwise. "round" and "fl" are
 * labels the UI may show; nothing in the app may require them.
 */
export type DraftFolderType =
  | "agenda"
  | "round"
  | "fl"
  | "topic"
  | "generic"
  | "unknown";

export type DraftFileType = "fl_summary" | "chair_draft" | "generic_draft" | "unknown";

export interface DraftFolder {
  id: string;
  meetingId: string;
  name: string;
  normalizedPath: string;
  sourceType: DraftSourceType;
  firstSeenAt: string;
  lastSeenAt: string;
  agendaItemId?: string | null;
  agendaConfidence: number;
  agendaMethod: string;
  parentFolderId?: string | null;
  parentPath?: string | null;
  depth: number;
  folderType: DraftFolderType;
  classificationConfidence: number;
  roundNumber?: number | null;
  url?: string | null;
  /** Files directly inside this folder. */
  fileCount: number;
  /** Files anywhere below this folder. */
  subtreeFileCount: number;
  removedAt?: string | null;
}

export interface DraftArtifactSource {
  sourceType: DraftSourceType;
  sourcePath: string;
  url?: string | null;
  firstSeenAt: string;
  lastSeenAt: string;
  size?: number | null;
  modifiedAt?: string | null;
}

export interface DraftRevision {
  revision: number;
  contentHash?: string | null;
  size?: number | null;
  modifiedAt?: string | null;
  firstSeenAt: string;
}

export interface DraftArtifact {
  id: string;
  meetingId: string;
  folderId: string;
  filename: string;
  normalizedPath: string;
  fileType: DraftFileType;
  classificationConfidence: number;
  documentKey: string;
  firstSeenAt: string;
  lastSeenAt: string;
  agendaItemId?: string | null;
  /** Normalized path of the containing folder, "" at the drafts root. */
  folderPath?: string | null;
  depth?: number;
  revision?: number | null;
  contentHash?: string | null;
  size?: number | null;
  modifiedAt?: string | null;
  sources: DraftArtifactSource[];
  revisions: DraftRevision[];
  removedAt?: string | null;
}

export interface DraftEvent {
  id: string;
  meetingId: string;
  eventType: DraftEventType;
  semanticType?: DraftSemanticType | null;
  detectedAt: string;
  sourceType: DraftSourceType;
  agendaItemId?: string | null;
  artifactId?: string | null;
  folderId?: string | null;
  title: string;
  detail?: string | null;
  fileType?: DraftFileType | null;
  folderPath?: string | null;
  roundNumber?: number | null;
  url?: string | null;
  /** Shared by a new folder and the files that arrived inside it. */
  groupKey?: string | null;
}

export interface DraftNotification {
  agendaItemId: string | null;
  bucketAt: string;
  detectedAt: string;
  total: number;
  counts: Partial<Record<DraftEventType, number>>;
  important: boolean;
  eventIds: string[];
  summary: string;
}

export interface DraftIndex {
  schemaVersion: number;
  meetingId: string;
  generatedAt: string;
  /** ok | delayed | baseline | inactive */
  scanState: string;
  lastSuccessfulScanAt?: string | null;
  baselinedAt?: string | null;
  monitoring: boolean;
  draftsRootUrl?: string | null;
  folders: DraftFolder[];
  artifacts: DraftArtifact[];
  events: DraftEvent[];
  newEventIds?: string[];
  unmappedFolders: string[];
  notifications?: DraftNotification[];
  message?: string | null;
}

/** Per-agenda-item rollup used across NOW, My agenda and the timetable. */
export interface AgendaActivity {
  agendaItemId: string;
  events: DraftEvent[];
  unread: DraftEvent[];
  unreadCount: number;
  flUpdates: number;
  newFiles: number;
  newRounds: number;
  newFolders: number;
  /** Total files currently indexed for this agenda item. */
  fileCount: number;
  /** How many of those are FL / moderator summaries. */
  flCount: number;
  latestFileAt?: string;
  latestAt?: string;
  latestFlSummary?: DraftArtifact;
}

/** What a user wants to be told about, stored on this device (no accounts). */
export interface DraftNotificationPrefs {
  scope: "my-agenda" | "followed" | "all";
  newFile: boolean;
  fileUpdated: boolean;
  flSummary: boolean;
  newFolder: boolean;
  fileRemoved: boolean;
  grouping: "immediate" | "grouped" | "important-only";
}
