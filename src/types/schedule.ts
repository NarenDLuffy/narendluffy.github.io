/**
 * Normalized RAN1 Live schedule data model.
 *
 * This model is intentionally decoupled from the DOCX layout of the 3GPP
 * chair / sub-chair schedules and from any single meeting. The Python
 * ingestion pipeline (see /ingestion) produces exactly these shapes as static
 * JSON, one directory per meeting:
 *
 *   public/data/meetings.json                       -> MeetingIndex
 *   public/data/meetings/<slug>/meeting.json        -> Meeting
 *   public/data/meetings/<slug>/schedule.json       -> { sessions, ingest }
 *   public/data/meetings/<slug>/rooms.json          -> Room[]
 *   public/data/meetings/<slug>/agenda.json         -> AgendaItem[]
 *   public/data/meetings/<slug>/sources.json        -> ScheduleSource[]
 *   public/data/meetings/<slug>/changes.json        -> ScheduleChange[]
 */

import type { Meeting } from "./meeting";

export type { Meeting, MeetingIndex, MeetingStatus, MeetingType } from "./meeting";

export interface Room {
  roomId: string;
  meetingId: string;
  roomName: string;
  shortName?: string;
  floor?: string;
  description?: string;
  /** Order used for timetable columns */
  order: number;
}

/**
 * Classification of a discovered document. Never inferred from a person's
 * name: chairs and sub-chairs change between meetings.
 */
export type SourceType =
  | "main_schedule"
  | "chair_schedule"
  | "subchair_schedule"
  | "online_schedule"
  | "offline_schedule"
  | "room_schedule"
  | "detailed_schedule"
  | "venue_information"
  | "unknown_schedule";

export type SourceOrigin = "public" | "meeting-local" | "manual";

export interface ScheduleSource {
  sourceId: string;
  meetingId: string;
  /** Original document file name */
  fileName: string;
  /** Human label, e.g. "Main v07" */
  label: string;
  type: SourceType;
  origin: SourceOrigin;
  /** Revision marker exactly as discovered, e.g. "v07" or "v07_1" */
  revision?: string;
  /** Sorting key derived from the revision, e.g. [7, 1] */
  revisionParts?: number[];
  url?: string;
  /** SHA-256 of the downloaded document */
  contentHash?: string;
  /** Server last-modified, never used alone to decide authority */
  modifiedAt?: string;
  retrievedAt: string;
  /** 0..1 parser confidence; low values surface in the admin review queue */
  confidence?: number;
}

export type SessionStatus = "scheduled" | "moved" | "cancelled" | "tentative";

export type SessionKind = "session" | "break" | "lunch" | "plenary" | "social";

export interface SessionSourceRef {
  sourceId: string;
  /** Which fields this source contributed */
  contributed: string[];
}

export interface Session {
  sessionId: string;
  meetingId: string;
  /** ISO date of the session day */
  date: string;
  /** Weekday label derived by the parser, e.g. "Tuesday" */
  day: string;
  /** Meeting-local time, HH:mm */
  startTime: string;
  endTime: string;
  roomId: string;
  roomName: string;
  topic: string;
  /** Topic key used for consistent colouring; discovered, not hard-coded */
  topicKey: string;
  agendaItems: string[];
  /** How the block is split between agenda items, when the chair stated it */
  agendaBreakdown?: AgendaSlot[];
  sessionLead?: string;
  mode?: "offline" | "online" | "hybrid";
  kind: SessionKind;
  status: SessionStatus;
  note?: string;
  sources: SessionSourceRef[];
}

/** One agenda item's share of a session block, e.g. 10.5.1.3 for 30 minutes */
export interface AgendaSlot {
  code?: string;
  label: string;
  minutes?: number;
  startTime?: string;
  endTime?: string;
}

export interface AgendaItem {
  code: string;
  meetingId: string;
  title: string;
  /** Parent agenda item code, e.g. 10.8 for 10.8.2 */
  parent?: string;
  topicKey?: string;
}

export type ChangeType =
  | "room_changed"
  | "start_time_changed"
  | "end_time_changed"
  | "session_added"
  | "session_removed"
  | "agenda_item_added"
  | "agenda_item_removed"
  | "agenda_item_moved"
  | "session_renamed"
  | "session_cancelled";

export interface ScheduleChange {
  changeId: string;
  meetingId: string;
  /** ISO timestamp when the change was detected */
  detectedAt: string;
  type: ChangeType;
  sessionId?: string;
  title: string;
  detail: string;
  agendaItems: string[];
  from?: string;
  to?: string;
  sourceIds: string[];
}

export interface ScheduleConflict {
  conflictId: string;
  meetingId: string;
  sessionId: string;
  field: string;
  values: { sourceId: string; value: string }[];
  resolved: boolean;
}

/** Health of the last ingestion attempt; drives the "update delayed" banner. */
export interface IngestStatus {
  /** ok = the published schedule is the newest validated parse */
  state: "ok" | "delayed" | "review_required";
  lastSuccessfulAt: string;
  lastAttemptAt?: string;
  message?: string;
}

export interface ScheduleBundle {
  /** Schema version so the frontend can reject incompatible output */
  schemaVersion: number;
  /** ISO timestamp of the last successful ingestion run */
  generatedAt: string;
  meeting: Meeting;
  rooms: Room[];
  sessions: Session[];
  agendaItems: AgendaItem[];
  sources: ScheduleSource[];
  changes: ScheduleChange[];
  conflicts: ScheduleConflict[];
  ingest: IngestStatus;
}
