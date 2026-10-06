import type { AgendaItem, Room, ScheduleBundle } from "@/types/schedule";

const ROOM_PALETTE = 8;

/** Stable colour per room, by its column order in the meeting. */
export function roomColor(room: Pick<Room, "order"> | undefined): string {
  if (!room) return "var(--muted-foreground)";
  if ("chairRole" in room && room.chairRole === "main") return "var(--room-main)";
  if ("sourceColor" in room && room.sourceColor) {
    const sourceColors: Record<string, string> = {
      D9D9D9: "var(--room-source-grey)",
      FFD966: "var(--room-source-orange)",
      F7CAAC: "var(--room-source-peach)",
      "9CC2E5": "var(--room-source-blue)",
    };
    const color = sourceColors[room.sourceColor.toUpperCase()];
    if (color) return color;
  }
  return `var(--room-${((room.order % ROOM_PALETTE) + ROOM_PALETTE) % ROOM_PALETTE})`;
}

export function roomStyle(room: Pick<Room, "order"> | undefined): React.CSSProperties {
  return { ["--room-color" as string]: roomColor(room) };
}

/** "1.1 Himalaya (RAN1 Brk2)" — session label in brackets when known. */
export function roomLabel(room: Pick<Room, "roomName" | "sessionLabel"> | undefined): string {
  if (!room) return "";
  const label = room.sessionLabel?.trim();
  if (!label || room.roomName.toLowerCase().includes(label.toLowerCase())) return room.roomName;
  return `${room.roomName} (${label})`;
}

export function roomLabelById(bundle: ScheduleBundle, roomId: string, fallback = ""): string {
  const room = bundle.rooms.find((r) => r.roomId === roomId);
  return room ? roomLabel(room) : fallback;
}

/** Rooms that actually host a session in this meeting's schedule. */
export function activeRooms(bundle: ScheduleBundle): Room[] {
  const used = new Set(bundle.sessions.map((s) => s.roomId).filter(Boolean));
  return bundle.rooms.filter((r) => used.has(r.roomId));
}

export function agendaTitle(items: AgendaItem[], code: string): string | undefined {
  return items.find((a) => a.code === code)?.title;
}
