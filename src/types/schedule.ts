/**
 * Normalized RAN1 Live schedule data model.
 *
 * This model is intentionally decoupled from the DOCX layout of the 3GPP
 * chair / sub-chair schedules. The Python ingestion pipeline (see /ingestion)
 * is responsible for producing exactly these shapes as static JSON:
 *
 *   public/schedule/schedule.json  -> ScheduleBundle
 *   public/schedule/changes.json   -> ScheduleChange[]
 *   public/schedule/sources.json   -> ScheduleSource[]
 */

export type MeetingStatus = "upcoming" | "live" | "closed";

export interface Meeting {
  meetingId: string;
  meetingName: string;
  /** ISO date, e.g. 2026-08-17 */
  startDate: string;
  endDate: string;
  venue: string;
  city: string;
  /** IANA timezone of the venue, e.g. Europe/Madrid */
  timezone: string;
  status: MeetingStatus;
}

export interface Room {
  roomId: string;
  roomName: string;
  /** Optional venue floor / area label */
  area?: string;
  /** Order used for timetable columns */
  order: number;
  capacityNote?: string;
}

export type SourceRole = "main" | "detail";

export interface ScheduleSource {
  sourceId: string;
  /** Original document file name */
  fileName: string;
  /** Human label, e.g. "Main v07" or "Hiroki v07.1" */
  label: string;
  role: SourceRole;
  /** Sub-chair / owner where applicable */
  owner?: string;
  url?: string;
  version?: string;
  /** ISO timestamp of when this document was last fetched */
  retrievedAt: string;
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
  /** Local venue time, HH:mm */
  startTime: string;
  endTime: string;
  roomId: string;
  roomName: string;
  topic: string;
  /** Topic key used for consistent colouring, e.g. "isac" */
  topicKey: string;
  agendaItems: string[];
  sessionLead?: string;
  /** online / offline / hybrid allocation from the main schedule */
  mode?: "offline" | "online" | "hybrid";
  kind: SessionKind;
  status: SessionStatus;
  note?: string;
  sources: SessionSourceRef[];
}

export interface AgendaItem {
  code: string;
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
  sessionId: string;
  field: string;
  values: { sourceId: string; value: string }[];
  resolved: boolean;
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
}
