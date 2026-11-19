import { setSelectedMeetingId } from "@/services/meetingSelection";
import { WORKING_GROUPS, setWorkingGroup, useWorkingGroup } from "@/lib/workingGroup";
import { cn } from "@/lib/utils";

/** RAN1 / RAN2 / RAN3 switch: the whole app follows the chosen working group. */
export function WorkingGroupSwitch() {
  const group = useWorkingGroup();
  return (
    <div
      role="radiogroup"
      aria-label="Working group"
      className="mono-code flex shrink-0 rounded-md border border-border p-0.5 text-xs font-semibold"
    >
      {WORKING_GROUPS.map((g) => (
        <button
          key={g}
          type="button"
          role="radio"
          aria-checked={group === g}
          onClick={() => {
            if (g === group) return;
            setSelectedMeetingId("");
            setWorkingGroup(g);
          }}
          className={cn(
            "rounded px-2 py-1 transition-colors",
            group === g ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {g}
        </button>
      ))}
    </div>
  );
}
