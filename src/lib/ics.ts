import type { ScheduleBundle, Session } from "@/types/schedule";

function pad(n: number) {
  return String(n).padStart(2, "0");
}

/**
 * Floating local time (no Z) so the entry lands on the venue clock regardless
 * of the device timezone — matching how delegates read the printed schedule.
 */
function dt(date: string, time: string) {
  const [y, m, d] = date.split("-").map(Number);
  const [hh, mm] = time.split(":").map(Number);
  return `${y}${pad(m ?? 1)}${pad(d ?? 1)}T${pad(hh ?? 0)}${pad(mm ?? 0)}00`;
}

function esc(text: string) {
  return text.replace(/([,;\\])/g, "\\$1").replace(/\n/g, "\\n");
}

export function buildIcs(bundle: ScheduleBundle, sessions: Session[]): string {
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//RAN1 Live//Unofficial RAN1 companion//EN",
    "CALSCALE:GREGORIAN",
    `X-WR-CALNAME:${esc(`${bundle.meeting.meetingName} — My agenda`)}`,
  ];

  sessions.forEach((s) => {
    lines.push(
      "BEGIN:VEVENT",
      `UID:${s.sessionId}@ran1live`,
      `DTSTAMP:${dt(bundle.meeting.startDate, "00:00")}Z`,
      `DTSTART;TZID=${bundle.meeting.timezone}:${dt(s.date, s.startTime)}`,
      `DTEND;TZID=${bundle.meeting.timezone}:${dt(s.date, s.endTime)}`,
      `SUMMARY:${esc(`${s.topic}${s.agendaItems.length ? ` (${s.agendaItems.join(", ")})` : ""}`)}`,
      `LOCATION:${esc(`${s.roomName}, ${bundle.meeting.venue}`)}`,
      `DESCRIPTION:${esc(
        [
          s.sessionLead ? `Lead: ${s.sessionLead}` : "",
          `Sources: ${s.sources.map((r) => r.sourceId).join(", ")}`,
          "Unofficial, automatically generated from RAN1 meeting documents.",
        ]
          .filter(Boolean)
          .join("\n"),
      )}`,
      "END:VEVENT",
    );
  });

  lines.push("END:VCALENDAR");
  return lines.join("\r\n");
}

export function downloadIcs(content: string, fileName: string) {
  const blob = new Blob([content], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  a.click();
  URL.revokeObjectURL(url);
}
