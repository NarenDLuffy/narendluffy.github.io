import { cn } from "@/lib/utils";

export function DayTabs({
  days,
  value,
  onChange,
}: {
  days: { date: string; day: string }[];
  value: string;
  onChange: (date: string) => void;
}) {
  return (
    <div className="flex gap-1 overflow-x-auto pb-1">
      {days.map((d) => (
        <button
          key={d.date}
          type="button"
          onClick={() => onChange(d.date)}
          className={cn(
            "min-h-10 shrink-0 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
            value === d.date
              ? "bg-primary text-primary-foreground"
              : "bg-secondary text-secondary-foreground hover:bg-accent",
          )}
        >
          {d.day.slice(0, 3)}
          <span className="mono-code ml-1.5 text-xs opacity-70">{d.date.slice(8)}</span>
        </button>
      ))}
    </div>
  );
}
