import { useQuery } from "@tanstack/react-query";
import { useSyncExternalStore } from "react";
import { meetingIndexQueryOptions, selectCurrentMeeting } from "@/services/meetingService";
import { getSelectedMeetingId, subscribeSelection } from "@/services/meetingSelection";
import { scheduleQueryOptions } from "@/services/scheduleService";
import { useMeetingClock } from "./useMeetingClock";
import { meetingTimeZone } from "@/lib/ics";
import { groupOfMeeting, useWorkingGroup } from "@/lib/workingGroup";

/**
 * The one place the app decides which meeting it is showing.
 *
 * Priority: an explicit archive selection, otherwise the automatically selected
 * current meeting (in progress -> nearest upcoming -> latest completed).
 */
export function useActiveMeeting(slug?: string) {
  const meetingsQuery = useQuery(meetingIndexQueryOptions);
  const selectedId = useSyncExternalStore(
    subscribeSelection,
    getSelectedMeetingId,
    () => "",
  );

  const group = useWorkingGroup();
  const allMeetings = meetingsQuery.data?.meetings ?? [];
  // Only the chosen working group's meetings (RAN1 or RAN2) are ever shown.
  const meetings = allMeetings.filter((m) => groupOfMeeting(m) === group);
  const current = selectCurrentMeeting(meetings);
  const explicit = slug
    ? allMeetings.find((m) => m.slug === slug)
    : selectedId
      ? meetings.find((m) => m.id === selectedId)
      : undefined;
  const meeting = explicit ?? current;

  const scheduleQuery = useQuery(scheduleQueryOptions(meeting));
  const clock = useMeetingClock(meeting ? meetingTimeZone(meeting) : "UTC");

  return {
    group,
    meetings,
    meeting,
    current,
    isCurrent: Boolean(meeting && current && meeting.id === current.id),
    result: scheduleQuery.data,
    bundle: scheduleQuery.data?.bundle ?? null,
    origin: scheduleQuery.data?.origin ?? "public",
    stale: scheduleQuery.data?.stale ?? false,
    isLoading: meetingsQuery.isLoading || (Boolean(meeting) && scheduleQuery.isLoading),
    clock,
  };
}
