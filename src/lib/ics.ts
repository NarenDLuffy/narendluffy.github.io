import type { ScheduleBundle, Session } from "@/types/schedule";

function pad(n: number) {
  return String(n).padStart(2, "0");
}

/**
 * Convert a meeting-local wall time (as printed in the RAN1 schedule) to a UTC
 * timestamp. Calendars then show the correct local time on any device, and
 * Outlook — which handles floating times and unknown TZIDs poorly — imports it
 * without shifting the event.
 */
function toUtcStamp(date: string, time: string, timeZone: string): string {
  const [y = 1970, m = 1, d = 1] = date.split("-").map(Number);
  const [hh = 0, mm = 0] = time.split(":").map(Number);
  // Start from the naive UTC instant, then correct by the zone offset at that
  // instant (two passes handle DST boundaries).
  let ts = Date.UTC(y, m - 1, d, hh, mm);
  for (let i = 0; i < 2; i += 1) {
    const offset = zoneOffsetMs(ts, timeZone);
    ts = Date.UTC(y, m - 1, d, hh, mm) - offset;
  }
  const dt = new Date(ts);
  return (
    `${dt.getUTCFullYear()}${pad(dt.getUTCMonth() + 1)}${pad(dt.getUTCDate())}` +
    `T${pad(dt.getUTCHours())}${pad(dt.getUTCMinutes())}00Z`
  );
}

function zoneOffsetMs(ts: number, timeZone: string): number {
  try {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone,
      hour12: false,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).formatToParts(new Date(ts));
    const get = (type: string) => Number(parts.find((p) => p.type === type)?.value ?? 0);
    const asUtc = Date.UTC(
      get("year"),
      get("month") - 1,
      get("day"),
      get("hour") % 24,
      get("minute"),
      get("second"),
    );
    return asUtc - ts;
  } catch {
    return 0;
  }
}

function esc(text: string) {
  return text.replace(/([,;\\])/g, "\\$1").replace(/\n/g, "\\n");
}

/** RFC 5545 requires content lines to be folded at 75 octets. */
function fold(line: string): string {
  if (line.length <= 73) return line;
  const chunks: string[] = [];
  let rest = line;
  chunks.push(rest.slice(0, 73));
  rest = rest.slice(73);
  while (rest.length) {
    chunks.push(` ${rest.slice(0, 72)}`);
    rest = rest.slice(72);
  }
  return chunks.join("\r\n");
}

export function buildIcs(bundle: ScheduleBundle, sessions: Session[]): string {
  const tz = bundle.meeting.timezone || "UTC";
  const stamp = toUtcStamp(bundle.meeting.startDate, "00:00", tz);
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//RAN1 Live//Unofficial RAN1 companion//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    `X-WR-CALNAME:${esc(`${bundle.meeting.name} — RAN1 Live`)}`,
    `X-WR-TIMEZONE:${tz}`,
  ];

  sessions.forEach((s) => {
    const breakdown = (s.agendaBreakdown ?? [])
      .map((slot) =>
        [slot.startTime && slot.endTime ? `${slot.startTime}–${slot.endTime}` : "", slot.label]
          .filter(Boolean)
          .join(" "),
      )
      .filter(Boolean);

    lines.push(
      "BEGIN:VEVENT",
      `UID:${s.sessionId}@ran1live`,
      `DTSTAMP:${stamp}`,
      `DTSTART:${toUtcStamp(s.date, s.startTime, tz)}`,
      `DTEND:${toUtcStamp(s.date, s.endTime, tz)}`,
      fold(
        `SUMMARY:${esc(
          `${s.topic}${s.agendaItems.length ? ` (${s.agendaItems.join(", ")})` : ""}`,
        )}`,
      ),
      fold(
        `LOCATION:${esc(
          [s.roomName, bundle.meeting.venue, bundle.meeting.city].filter(Boolean).join(", "),
        )}`,
      ),
      fold(
        `DESCRIPTION:${esc(
          [
            s.agendaItems.length ? `Agenda items: ${s.agendaItems.join(", ")}` : "",
            breakdown.length ? `Breakdown: ${breakdown.join(" | ")}` : "",
            s.sessionLead ? `Lead: ${s.sessionLead}` : "",
            s.note ?? "",
            `Meeting time (${tz}): ${s.date} ${s.startTime}–${s.endTime}`,
            `Sources: ${s.sources.map((r) => r.sourceId).join(", ")}`,
            "Unofficial, automatically generated from RAN1 meeting documents.",
          ]
            .filter(Boolean)
            .join("\n"),
        )}`,
      ),
      s.status === "cancelled" ? "STATUS:CANCELLED" : "STATUS:CONFIRMED",
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
