import type { ScheduleBundle, Session } from "@/types/schedule";

/**
 * DEVELOPMENT DATA ONLY (Phase 1).
 *
 * This mirrors the exact shape the Python ingestion pipeline will emit into
 * public/schedule/schedule.json. Nothing here may be treated as application
 * logic: rooms, topics and agenda items always come from the loaded bundle.
 */

const MEETING_ID = "RAN1-126";

const DAYS = [
  { date: "2026-08-17", day: "Monday" },
  { date: "2026-08-18", day: "Tuesday" },
  { date: "2026-08-19", day: "Wednesday" },
  { date: "2026-08-20", day: "Thursday" },
  { date: "2026-08-21", day: "Friday" },
];

const ROOMS = [
  { roomId: "expo-foyer", roomName: "Expo Foyer", area: "Level 0", order: 1 },
  { roomId: "praetorium", roomName: "Praetorium", area: "Level 0", order: 2 },
  { roomId: "himalaya", roomName: "1.1 Himalaya", area: "Level 1", order: 3 },
  {
    roomId: "madrid-lisbon",
    roomName: "0.6/0.7 Madrid/Lisbon",
    area: "Level 0",
    order: 4,
  },
  { roomId: "brussels", roomName: "0.4 Brussels", area: "Level 0", order: 5 },
];

const TOPICS: Record<string, { topic: string; lead: string; items: string[] }> = {
  isac: { topic: "6G ISAC", lead: "Hiroki", items: ["10.8.1", "10.8.2", "10.8.3"] },
  waveform: { topic: "6G Waveform", lead: "Sorour", items: ["10.2.1"] },
  aiot: { topic: "A-IoT", lead: "Wei", items: ["9.3.1", "9.3.2", "9.3.3"] },
  aiml: { topic: "AI/ML", lead: "Sorour", items: ["10.5.4.1", "10.5.4.2", "10.5.4.3"] },
  mimo: { topic: "MIMO", lead: "Younsun", items: ["10.4.1", "10.4.2"] },
  ntn: { topic: "NTN", lead: "Xiaodong", items: ["9.6.1"] },
  maintenance: { topic: "Maintenance", lead: "Chair", items: ["8.1"] },
};

interface Slot {
  start: string;
  end: string;
  room: string;
  topicKey: string;
  items?: string[];
  lead?: string;
}

const DAY_PLANS: Slot[][] = [
  // Monday
  [
    { start: "09:00", end: "10:30", room: "praetorium", topicKey: "maintenance" },
    { start: "09:00", end: "10:30", room: "himalaya", topicKey: "isac", items: ["10.8.1"] },
    { start: "11:00", end: "12:30", room: "himalaya", topicKey: "isac", items: ["10.8.2"] },
    { start: "11:00", end: "12:30", room: "madrid-lisbon", topicKey: "aiml", items: ["10.5.4.1"] },
    { start: "14:00", end: "15:30", room: "praetorium", topicKey: "mimo", items: ["10.4.1"] },
    { start: "14:00", end: "15:30", room: "brussels", topicKey: "aiot", items: ["9.3.1"] },
    { start: "16:00", end: "17:30", room: "himalaya", topicKey: "waveform", items: ["10.2.1"] },
    { start: "16:00", end: "17:30", room: "madrid-lisbon", topicKey: "ntn", items: ["9.6.1"] },
  ],
  // Tuesday
  [
    { start: "08:30", end: "10:00", room: "praetorium", topicKey: "mimo", items: ["10.4.2"] },
    { start: "08:30", end: "10:00", room: "brussels", topicKey: "aiot", items: ["9.3.2"] },
    { start: "10:30", end: "12:00", room: "himalaya", topicKey: "isac", items: ["10.8.2"] },
    { start: "10:30", end: "12:00", room: "madrid-lisbon", topicKey: "aiml", items: ["10.5.4.2"] },
    { start: "14:30", end: "15:30", room: "himalaya", topicKey: "isac", items: ["10.8.2"] },
    { start: "14:30", end: "16:00", room: "praetorium", topicKey: "waveform", items: ["10.2.1"] },
    { start: "16:00", end: "17:30", room: "brussels", topicKey: "aiot", items: ["9.3.3"] },
    { start: "16:30", end: "18:00", room: "madrid-lisbon", topicKey: "aiml", items: ["10.5.4.3"] },
  ],
  // Wednesday
  [
    { start: "09:00", end: "10:30", room: "himalaya", topicKey: "isac", items: ["10.8.3"] },
    { start: "09:00", end: "10:30", room: "praetorium", topicKey: "mimo", items: ["10.4.1"] },
    { start: "11:00", end: "12:30", room: "madrid-lisbon", topicKey: "aiml", items: ["10.5.4.1"] },
    { start: "11:00", end: "12:30", room: "brussels", topicKey: "ntn", items: ["9.6.1"] },
    { start: "14:00", end: "16:00", room: "praetorium", topicKey: "maintenance" },
    { start: "14:00", end: "15:30", room: "himalaya", topicKey: "waveform", items: ["10.2.1"] },
    { start: "16:30", end: "18:00", room: "brussels", topicKey: "aiot", items: ["9.3.1"] },
  ],
  // Thursday
  [
    { start: "08:30", end: "10:00", room: "himalaya", topicKey: "isac", items: ["10.8.1"] },
    { start: "08:30", end: "10:00", room: "madrid-lisbon", topicKey: "aiml", items: ["10.5.4.2"] },
    { start: "10:30", end: "12:00", room: "praetorium", topicKey: "mimo", items: ["10.4.2"] },
    { start: "10:30", end: "12:00", room: "brussels", topicKey: "aiot", items: ["9.3.2"] },
    { start: "14:00", end: "15:30", room: "himalaya", topicKey: "isac", items: ["10.8.3"] },
    { start: "14:00", end: "15:30", room: "madrid-lisbon", topicKey: "waveform", items: ["10.2.1"] },
    { start: "16:00", end: "17:30", room: "praetorium", topicKey: "aiml", items: ["10.5.4.3"] },
  ],
  // Friday
  [
    { start: "08:30", end: "10:00", room: "himalaya", topicKey: "isac", items: ["10.8.2"] },
    { start: "08:30", end: "10:00", room: "praetorium", topicKey: "mimo", items: ["10.4.1"] },
    { start: "10:30", end: "12:00", room: "madrid-lisbon", topicKey: "aiml", items: ["10.5.4.3"] },
    { start: "10:30", end: "12:00", room: "brussels", topicKey: "aiot", items: ["9.3.3"] },
    { start: "13:30", end: "15:00", room: "praetorium", topicKey: "maintenance" },
    { start: "15:30", end: "17:00", room: "praetorium", topicKey: "waveform", items: ["10.2.1"] },
  ],
];

const BREAKS: Slot[] = [
  { start: "10:00", end: "10:30", room: "expo-foyer", topicKey: "break" },
  { start: "12:30", end: "14:00", room: "expo-foyer", topicKey: "lunch" },
  { start: "15:30", end: "16:00", room: "expo-foyer", topicKey: "break" },
];

function roomName(roomId: string) {
  return ROOMS.find((r) => r.roomId === roomId)?.roomName ?? roomId;
}

function buildSessions(): Session[] {
  const sessions: Session[] = [];

  DAYS.forEach((d, dayIndex) => {
    (DAY_PLANS[dayIndex] ?? []).forEach((slot, i) => {
      const t = TOPICS[slot.topicKey]!;
      const items = slot.items ?? t.items.slice(0, 1);
      const detailed = slot.topicKey === "isac" || slot.topicKey === "aiml";
      sessions.push({
        sessionId: `${MEETING_ID}-${d.date}-${slot.room}-${i}`,
        meetingId: MEETING_ID,
        date: d.date,
        day: d.day,
        startTime: slot.start,
        endTime: slot.end,
        roomId: slot.room,
        roomName: roomName(slot.room),
        topic: t.topic,
        topicKey: slot.topicKey,
        agendaItems: items,
        sessionLead: slot.lead ?? t.lead,
        mode: "offline",
        kind: slot.topicKey === "maintenance" ? "plenary" : "session",
        status: "scheduled",
        sources: detailed
          ? [
              { sourceId: "main-v07", contributed: ["room", "startTime", "endTime"] },
              {
                sourceId: slot.topicKey === "isac" ? "hiroki-v07-1" : "sorour-v03",
                contributed: ["agendaItems", "sessionLead", "topic"],
              },
            ]
          : [
              {
                sourceId: "main-v07",
                contributed: ["room", "startTime", "endTime", "topic", "agendaItems"],
              },
            ],
      });
    });

    BREAKS.forEach((b, i) => {
      sessions.push({
        sessionId: `${MEETING_ID}-${d.date}-break-${i}`,
        meetingId: MEETING_ID,
        date: d.date,
        day: d.day,
        startTime: b.start,
        endTime: b.end,
        roomId: b.room,
        roomName: roomName(b.room),
        topic: b.topicKey === "lunch" ? "Lunch" : "Coffee break",
        topicKey: b.topicKey,
        agendaItems: [],
        kind: b.topicKey === "lunch" ? "lunch" : "break",
        status: "scheduled",
        sources: [{ sourceId: "main-v07", contributed: ["startTime", "endTime"] }],
      });
    });
  });

  return sessions.sort((a, b) =>
    (a.date + a.startTime).localeCompare(b.date + b.startTime),
  );
}

export const mockSchedule: ScheduleBundle = {
  schemaVersion: 1,
  generatedAt: "2026-08-21T12:37:00Z",
  meeting: {
    meetingId: MEETING_ID,
    meetingName: "RAN1#126",
    startDate: "2026-08-17",
    endDate: "2026-08-21",
    venue: "Fira Barcelona Gran Via",
    city: "Barcelona",
    timezone: "Europe/Madrid",
    status: "live",
  },
  rooms: ROOMS,
  sessions: buildSessions(),
  agendaItems: [
    { code: "8.1", title: "NR maintenance", topicKey: "maintenance" },
    { code: "9.3", title: "Ambient IoT", topicKey: "aiot" },
    { code: "9.3.1", title: "A-IoT physical layer design", parent: "9.3", topicKey: "aiot" },
    { code: "9.3.2", title: "A-IoT procedures", parent: "9.3", topicKey: "aiot" },
    { code: "9.3.3", title: "A-IoT coexistence", parent: "9.3", topicKey: "aiot" },
    { code: "9.6", title: "NTN enhancements", topicKey: "ntn" },
    { code: "9.6.1", title: "NTN downlink coverage", parent: "9.6", topicKey: "ntn" },
    { code: "10.2", title: "6G waveform", topicKey: "waveform" },
    { code: "10.2.1", title: "Waveform candidates evaluation", parent: "10.2", topicKey: "waveform" },
    { code: "10.4", title: "6G MIMO", topicKey: "mimo" },
    { code: "10.4.1", title: "MIMO framework", parent: "10.4", topicKey: "mimo" },
    { code: "10.4.2", title: "CSI acquisition", parent: "10.4", topicKey: "mimo" },
    { code: "10.5", title: "AI/ML air interface", topicKey: "aiml" },
    { code: "10.5.4", title: "AI/ML model lifecycle", parent: "10.5", topicKey: "aiml" },
    { code: "10.5.4.1", title: "Model identification", parent: "10.5.4", topicKey: "aiml" },
    { code: "10.5.4.2", title: "Model monitoring", parent: "10.5.4", topicKey: "aiml" },
    { code: "10.5.4.3", title: "Model transfer", parent: "10.5.4", topicKey: "aiml" },
    { code: "10.8", title: "6G ISAC", topicKey: "isac" },
    { code: "10.8.1", title: "ISAC deployment scenarios", parent: "10.8", topicKey: "isac" },
    { code: "10.8.2", title: "ISAC channel modelling", parent: "10.8", topicKey: "isac" },
    { code: "10.8.3", title: "ISAC evaluation methodology", parent: "10.8", topicKey: "isac" },
  ],
  sources: [
    {
      sourceId: "main-v07",
      fileName: "Draft RAN1#126 online and offline schedules - v07.docx",
      label: "Main v07",
      role: "main",
      owner: "RAN1 Chair",
      version: "v07",
      retrievedAt: "2026-08-21T12:34:00Z",
    },
    {
      sourceId: "hiroki-v07-1",
      fileName: "RAN1#126 schedule for Hiroki Adhoc2 sessions_v07_1.docx",
      label: "Hiroki v07.1",
      role: "detail",
      owner: "Hiroki",
      version: "v07.1",
      retrievedAt: "2026-08-21T12:34:00Z",
    },
    {
      sourceId: "sorour-v03",
      fileName: "RAN1#126 Sorour sessions schedule v03.docx",
      label: "Sorour v03",
      role: "detail",
      owner: "Sorour",
      version: "v03",
      retrievedAt: "2026-08-21T11:02:00Z",
    },
  ],
  changes: [
    {
      changeId: "c1",
      meetingId: MEETING_ID,
      detectedAt: "2026-08-21T12:37:00Z",
      type: "room_changed",
      title: "AI 10.8.2 moved",
      detail: "ISAC channel modelling changed room",
      agendaItems: ["10.8.2"],
      from: "1.1 Himalaya",
      to: "0.6/0.7 Madrid/Lisbon",
      sourceIds: ["hiroki-v07-1"],
    },
    {
      changeId: "c2",
      meetingId: MEETING_ID,
      detectedAt: "2026-08-21T11:58:00Z",
      type: "end_time_changed",
      title: "6G Waveform extended",
      detail: "Session end time extended",
      agendaItems: ["10.2.1"],
      from: "16:30",
      to: "17:00",
      sourceIds: ["main-v07"],
    },
    {
      changeId: "c3",
      meetingId: MEETING_ID,
      detectedAt: "2026-08-21T09:12:00Z",
      type: "agenda_item_added",
      title: "AI 10.5.4.3 added",
      detail: "Model transfer added to Friday AI/ML session",
      agendaItems: ["10.5.4.3"],
      to: "0.6/0.7 Madrid/Lisbon 10:30-12:00",
      sourceIds: ["sorour-v03"],
    },
    {
      changeId: "c4",
      meetingId: MEETING_ID,
      detectedAt: "2026-08-20T18:40:00Z",
      type: "session_added",
      title: "A-IoT extra session added",
      detail: "Additional A-IoT session on Friday morning",
      agendaItems: ["9.3.3"],
      to: "0.4 Brussels 10:30-12:00",
      sourceIds: ["main-v07"],
    },
  ],
  conflicts: [
    {
      conflictId: "x1",
      sessionId: `${MEETING_ID}-2026-08-21-himalaya-0`,
      field: "roomId",
      values: [
        { sourceId: "main-v07", value: "himalaya" },
        { sourceId: "hiroki-v07-1", value: "madrid-lisbon" },
      ],
      resolved: false,
    },
  ],
};
