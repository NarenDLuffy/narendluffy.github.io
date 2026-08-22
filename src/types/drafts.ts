/**
 * Draft tracker model — mirror of `draft_tracker/models.py`.
 *
 * Published per meeting as public/data/meetings/<slug>/drafts.json by the
 * draft-watch workflow. A logical artifact is modelled separately from its
 * source appearances, so a file seen first on the meeting-local server and
 * later on the public 3GPP site stays one artifact with one notification.
 */

export type DraftSourceType = "public" | "meeting-local";

export type DraftEventType =
  | "NEW_FILE"
  | "FILE_UPDATED"
  | "NEW_FOLDER"
  | "NEW_ROUND"
  | "FL_SUMMARY_UPDATED"
  | "FILE_REMOVED";

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
  roundNumber?: number | null;
  depth: number;
  url?: string | null;
  fileCount: number;
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
  newRound: boolean;
  fileRemoved: boolean;
  grouping: "immediate" | "grouped" | "important-only";
}
