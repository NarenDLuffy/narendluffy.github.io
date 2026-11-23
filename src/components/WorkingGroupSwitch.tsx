import { setSelectedMeetingId } from "@/services/meetingSelection";
import { WORKING_GROUPS, groupLabel, setWorkingGroup, useWorkingGroup } from "@/lib/workingGroup";
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { WorkingGroup } from "@/types/meeting";

/** Groups on the roadmap; listed so delegates see what is coming, not selectable yet. */
const COMING_SOON = ["SA1"];

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
        <SelectGroup>
          <SelectLabel className="text-xs text-muted-foreground">Coming soon</SelectLabel>
          {COMING_SOON.map((g) => (
            <SelectItem key={g} value={`soon:${g}`} disabled className="mono-code text-xs">
              {g}
            </SelectItem>
          ))}
        </SelectGroup>
      </SelectContent>
    </Select>
  );
}
