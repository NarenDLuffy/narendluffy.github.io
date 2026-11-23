import { setSelectedMeetingId } from "@/services/meetingSelection";
import { WORKING_GROUPS, groupLabel, setWorkingGroup, useWorkingGroup } from "@/lib/workingGroup";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { WorkingGroup } from "@/types/meeting";

/** Working-group dropdown: the whole app follows the chosen group. */
export function WorkingGroupSwitch() {
  const group = useWorkingGroup();
  return (
    <Select
      value={group}
      onValueChange={(g) => {
        if (g === group) return;
        setSelectedMeetingId("");
        setWorkingGroup(g as WorkingGroup);
      }}
    >
      <SelectTrigger aria-label="Working group" className="mono-code h-8 w-[124px] shrink-0 text-xs font-semibold">
        <SelectValue>{groupLabel(group)}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        {WORKING_GROUPS.map((g) => (
          <SelectItem key={g} value={g} className="mono-code text-xs">
            {groupLabel(g)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
