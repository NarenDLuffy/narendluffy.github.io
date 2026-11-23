import { createFileRoute } from "@tanstack/react-router";
import { authenticateCronRequest } from "@/integrations/supabase/cron-auth";
import { parseListing } from "@/lib/listingParser";

// GitHub's own timer skips/delays scheduled runs for hours when busy. This job
// (called every 5 minutes by the backend scheduler) starts the timetable
// updater as soon as Meetings Sync holds a schedule file newer than the last run.
const REPO = "NarenDLuffy/narendluffy.github.io";
const WORKFLOW = "update-schedule.yml";
const DATA = `https://raw.githubusercontent.com/${REPO}/main/public/data/`;
const INBOX = "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN1/Inbox/";
// RAN2 keeps its single week grid in the Agenda folder.
const RAN2_AGENDA = "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN2/Agenda/";
// RAN3: main session in the chair notes, offlines in the room spreadsheet.
// RAN Plenary: the chair's "RAN#<n> time plan vNN" in Inbox/Chair.
const RANP_CHAIR = "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN/Inbox/Chair/";
// RAN4: "RAN4_<n>_meeting_schedule_vNN.pptx" + topic list in Meeting_Arrangements.
const SA2_PLANS = "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/SA2/Inbox/Drafts/_Session_Plan_Updates/";
const SA1_AGENDA = "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/SA1/Inbox/agenda/";
const RAN4_ARR = "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN4/Inbox/Meeting_Arrangements/";
const RAN3_SOURCES = [
  "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN3/Inbox/Chairs_Notes/",
  "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN3/Offline_meeting_room/",
];
const UA = { "User-Agent": "Mozilla/5.0 (ran1-live schedule watch)" };
const DAY = 86_400_000;

async function text(url: string): Promise<string | null> {
  try {
    const res = await fetch(url, { headers: UA, signal: AbortSignal.timeout(15_000) });
    return res.ok ? await res.text() : null;
  } catch {
    return null;
  }
}

async function newestIn(
  folders: string[],
  accept: (name: string) => boolean = (n) => /schedul/i.test(n) && /\.docx$/i.test(n),
): Promise<{ newest: number; name: string }> {
  let newest = 0;
  let name = "";
  for (const folder of folders) {
    const html = await text(folder);
    if (!html) continue;
    for (const f of parseListing(html, folder)) {
      if (f.isDir || !accept(f.name)) continue;
      const t = Date.parse(f.modifiedAt ?? "") || 0;
      if (t > newest) {
        newest = t;
        name = f.name;
      }
    }
  }
  return { newest, name };
}

async function newestInInbox(inbox: string): Promise<{ newest: number; name: string }> {
  const html = await text(inbox);
  if (!html) return { newest: 0, name: "" };
  const folders = parseListing(html, inbox)
    .filter((e) => e.isDir && /notes|chair|schedul/i.test(e.name))
    .map((e) => e.href);
  return newestIn(folders);
}

export const Route = createFileRoute("/api/public/jobs/schedule-watch")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const authFailure = await authenticateCronRequest(request);
        if (authFailure) return authFailure;

        const meetings = JSON.parse((await text(`${DATA}meetings.json?t=${Date.now()}`)) ?? "{}");
        const now = Date.now();
        // Every followed working group (RAN1, RAN2) with a meeting running now.
        const live = (meetings.meetings ?? []).filter(
          (m: { status: string; startDate: string; endDate: string }) => {
            const start = Date.parse(`${m.startDate}T00:00:00Z`);
            const end = Date.parse(`${m.endDate}T23:59:59Z`);
            // Meetings Sync is read only on meeting days and the day after.
            return now >= start && now <= end + DAY;
          },
        ) as { slug: string; workingGroup?: string }[];
        if (live.length === 0) return Response.json({ action: "none", reason: "not meeting week" });

        let due = "";
        for (const m of live) {
          const health = JSON.parse(
            (await text(`${DATA}meetings/${m.slug}/health.json?t=${now}`)) ?? "{}",
          );
          const lastRun = Date.parse(health?.schedule?.lastAttemptAt ?? "") || 0;
          const ran2 = m.workingGroup === "RAN2" || m.slug.startsWith("ran2-");
          const ran3 = m.workingGroup === "RAN3" || m.slug.startsWith("ran3-");
          const ranp = m.workingGroup === "RAN" || m.slug.startsWith("ran-");
          const ran4 = m.workingGroup === "RAN4" || m.slug.startsWith("ran4-");
          const sa2 = m.workingGroup === "SA2" || m.slug.startsWith("sa2-");
          const sa1 = m.workingGroup === "SA1" || m.slug.startsWith("sa1-");
          const { newest, name } = sa1
            ? await newestIn([SA1_AGENDA], (n) => /(breakout.*schedule|agenda for).*\.docx$/i.test(n))
            : sa2
            ? await newestIn([SA2_PLANS], (n) => /session\s*plan.*\.(docx|zip)$/i.test(n))
            : ran4
            ? await newestIn([RAN4_ARR], (n) => /meeting_schedule.*\.pptx$|list_topics.*\.xlsx$/i.test(n))
            : ranp
            ? await newestIn([RANP_CHAIR], (n) => /time\s*plan.*\.(docx|zip)$/i.test(n))
            : ran3
            ? await newestIn(RAN3_SOURCES, (n) => /agenda.*\.docx$|offline.*\.xlsx$/i.test(n))
            : ran2
              ? await newestIn([RAN2_AGENDA])
              : await newestInInbox(INBOX);
          if (newest > lastRun) {
            due = name;
            break;
          }
        }
        if (!due) return Response.json({ action: "none", reason: "up to date" });
        const newestName = due;

        const token = process.env['GITHUB_DISPATCH_TOKEN'];
        if (!token) return Response.json({ action: "none", reason: "GITHUB_DISPATCH_TOKEN missing", newestName });
        const gh = {
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github+json",
          "User-Agent": "ran1-live",
        };
        const api = `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}`;
        for (const status of ["queued", "in_progress"]) {
          const r = await fetch(`${api}/runs?status=${status}&per_page=1`, { headers: gh });
          if (r.ok && ((await r.json()) as { total_count: number }).total_count > 0) {
            return Response.json({ action: "none", reason: `run ${status}`, newestName });
          }
        }
        const res = await fetch(`${api}/dispatches`, {
          method: "POST",
          headers: { ...gh, "Content-Type": "application/json" },
          body: JSON.stringify({ ref: "main" }),
        });
        if (!res.ok) {
          const body = await res.text();
          console.error(`GitHub dispatch failed [${res.status}]: ${body}`);
          return Response.json({ action: "failed", status: res.status, body }, { status: 502 });
        }
        return Response.json({ action: "dispatched", newestName });
      },
    },
  },
});
