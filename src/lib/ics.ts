import type { Meeting, ScheduleBundle, Session } from "@/types/schedule";
import type { Deadline } from "@/hooks/useDeadlines";
import { agendaTitle, roomLabelById } from "@/lib/rooms";

/**
 * The 3GPP portal sometimes reports a fixed offset ("Etc/GMT+6") for host
 * cities that observe daylight saving. Those are mapped to the real zone so a
 * Dallas or Calgary meeting is not an hour off in summer.
 */
const CITY_ZONES: Record<string, string> = {
  dallas: "America/Chicago",
  chicago: "America/Chicago",
  calgary: "America/Edmonton",
  toronto: "America/Toronto",
  vancouver: "America/Vancouver",
  "san diego": "America/Los_Angeles",
  "san francisco": "America/Los_Angeles",
  "new york": "America/New_York",
  atlanta: "America/New_York",
  orlando: "America/New_York",
  honolulu: "Pacific/Honolulu",
};

export function meetingTimeZone(meeting: Pick<Meeting, "timezone" | "city">): string {
  const tz = meeting.timezone || "UTC";
  const city = (meeting.city ?? "").toLowerCase().trim();
  if ((tz.startsWith("Etc/") || tz === "UTC") && CITY_ZONES[city]) return CITY_ZONES[city];
  try {
    new Intl.DateTimeFormat("en-US", { timeZone: tz });
    return tz;
  } catch {
    return CITY_ZONES[city] ?? "UTC";
  }
}

function pad(n: number) {
  return String(n).padStart(2, "0");
}

/**
 * Convert a meeting-local wall time (as printed in the RAN1 schedule) to a UTC
 * timestamp. Calendars then show the correct local time on any device, and
 * Outlook — which handles floating times and unknown TZIDs poorly — imports it
 * without shifting the event.
 */
export function toUtcStamp(date: string, time: string, timeZone: string): string {
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

/** RFC 5545: fold content lines at 75 octets (UTF-8 bytes, not characters). */
function fold(line: string): string {
  const enc = new TextEncoder();
  const out: string[] = [];
  let current = "";
  let bytes = 0;
  for (const ch of line) {
    const size = enc.encode(ch).length;
    const limit = out.length === 0 ? 75 : 74;
    if (bytes + size > limit) {
      out.push(current);
      current = "";
      bytes = 0;
    }
    current += ch;
    bytes += size;
  }
  out.push(current);
  return out.join("\r\n ");
}

export function buildIcs(
  bundle: ScheduleBundle,
  sessions: Session[],
  deadlines: Deadline[] = [],
): string {
  const tz = meetingTimeZone(bundle.meeting);
  const now = new Date();
  const stamp =
    `${now.getUTCFullYear()}${pad(now.getUTCMonth() + 1)}${pad(now.getUTCDate())}` +
    `T${pad(now.getUTCHours())}${pad(now.getUTCMinutes())}00Z`;
  const named = (code: string) => {
    const title = agendaTitle(bundle.agendaItems, code);
    return title ? `${code} ${title}` : code;
  };
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
          [roomLabelById(bundle, s.roomId, s.roomName), bundle.meeting.venue, bundle.meeting.city].filter(Boolean).join(", "),
        )}`,
      ),
      fold(
        `DESCRIPTION:${esc(
          [
            s.agendaItems.length ? `Agenda items:\n${s.agendaItems.map(named).join("\n")}` : "",
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

  deadlines.forEach((d) => {
    const start = toUtcStamp(d.date, d.time, tz);
    lines.push(
      "BEGIN:VEVENT",
      `UID:deadline-${d.id}@ran1live`,
      `DTSTAMP:${stamp}`,
      `DTSTART:${start}`,
      `DTEND:${start}`,
      fold(`SUMMARY:${esc(`${d.label} due: ${named(d.code)}`)}`),
      fold(`DESCRIPTION:${esc(`Meeting time (${tz}): ${d.date} ${d.time}`)}`),
      "BEGIN:VALARM",
      "ACTION:DISPLAY",
      "TRIGGER:-PT30M",
      fold(`DESCRIPTION:${esc(`${d.label} due in 30 min (${d.code})`)}`),
      "END:VALARM",
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
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  // iOS Safari reads the blob asynchronously; revoking at once breaks the download.
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
