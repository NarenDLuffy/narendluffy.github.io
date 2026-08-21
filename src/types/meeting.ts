/**
 * Meeting model for RAN1 Live.
 *
 * Nothing in the application may assume a specific RAN1 meeting. A meeting is
 * discovered by the ingestion pipeline (see /ingestion/meeting_discovery.py),
 * published into public/data/meetings.json and consumed generically here.
 *
 * `id` is a stable internal identifier that never changes once minted.
 * `name` is the display name and may follow any future 3GPP convention.
 */

export type MeetingType = "regular" | "bis" | "adhoc" | "other";

export type MeetingStatus = "upcoming" | "active" | "completed";

export interface MeetingSourceFolders {
  /** Public 3GPP meeting folder, e.g. .../tsg_ran/WG1_RL1/TSGR1_126/ */
  meetingFolder?: string;
  /** RAN1 Inbox folder used during the meeting week */
  inbox?: string;
  /** Chair notes folder inside the Inbox */
  chairNotes?: string;
  /** Agenda folder / agenda file location */
  agenda?: string;
}

export interface Meeting {
  /** Stable internal id, e.g. "ran1-126" — never derived from display text at runtime */
  id: string;
  /** URL-safe slug used for /meetings/:slug and public/data/meetings/:slug */
  slug: string;
  /** Display name exactly as 3GPP writes it, e.g. "RAN1#126" or "RAN1#127-bis" */
  name: string;
  meetingNumber?: number;
  type: MeetingType;
  /** ISO date (meeting-local calendar day) */
  startDate: string;
  endDate: string;
  /** IANA timezone of the venue */
  timezone: string;
  venue?: string;
  city?: string;
  country?: string;
  status: MeetingStatus;
  /** Set by the ingestion pipeline once a schedule document has been parsed */
  schedulePublished?: boolean;
  /** Administrator override of the automatically calculated status */
  statusOverride?: MeetingStatus;
  sources?: MeetingSourceFolders;
  /** Floorplan / venue information discovered with the meeting */
  floorplanUrl?: string;
  /** ISO timestamp of the last successful ingestion run for this meeting */
  lastIngestedAt?: string;
}

export interface MeetingIndex {
  schemaVersion: number;
  generatedAt: string;
  meetings: Meeting[];
}
