/**
 * Company presence types.
 *
 * Presence is always scoped to a single meeting: when a meeting rolls over,
 * nobody may still appear checked into a room of the previous meeting.
 * Cross-company isolation is enforced in the database, never in the browser.
 */

export interface CurrentPresence {
  userId: string;
  organizationId: string;
  meetingId: string;
  roomId: string;
  sessionId?: string;
  displayName?: string;
  /** ISO timestamps */
  updatedAt: string;
  expiresAt: string;
}

export interface CoverageRow {
  meetingId: string;
  sessionId: string;
  topic: string;
  agendaItems: string[];
  roomId: string;
  roomName: string;
  startTime: string;
  endTime: string;
  colleaguesPresent: number;
  colleaguesFollowing: number;
}
