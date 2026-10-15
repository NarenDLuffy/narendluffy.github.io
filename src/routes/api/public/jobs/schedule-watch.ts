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

export const Route = createFileRoute("/api/public/jobs/schedule-watch")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const authFailure = await authenticateCronRequest(request);
        if (authFailure) return authFailure;

        const meetings = JSON.parse((await text(`${DATA}meetings.json?t=${Date.now()}`)) ?? "{}");
        const active = (meetings.meetings ?? []).find((m: { status: string }) => m.status === "active");
        if (!active) return Response.json({ action: "none", reason: "no active meeting" });
        const now = Date.now();
        const start = Date.parse(`${active.startDate}T00:00:00Z`);
        const end = Date.parse(`${active.endDate}T23:59:59Z`);
        // Meetings Sync is read only on meeting days and the day after.
        if (now < start || now > end + DAY) return Response.json({ action: "none", reason: "not meeting week" });

        const health = JSON.parse(
          (await text(`${DATA}meetings/${active.slug}/health.json?t=${now}`)) ?? "{}",
        );
        const lastRun = Date.parse(health?.schedule?.lastAttemptAt ?? "") || 0;

        const inboxHtml = await text(INBOX);
        if (!inboxHtml) return Response.json({ action: "none", reason: "inbox unreachable" });
        const folders = parseListing(inboxHtml, INBOX).filter(
          (e) => e.isDir && /notes|chair|schedul/i.test(e.name),
        );
        let newest = 0;
        let newestName = "";
        for (const folder of folders) {
          const html = await text(folder.href);
          if (!html) continue;
          for (const f of parseListing(html, folder.href)) {
            if (f.isDir || !/schedul/i.test(f.name) || !/\.docx$/i.test(f.name)) continue;
            const t = Date.parse(f.modifiedAt ?? "") || 0;
            if (t > newest) {
              newest = t;
              newestName = f.name;
            }
          }
        }
        if (newest <= lastRun) return Response.json({ action: "none", reason: "up to date", newestName });

        const token = process.env.GITHUB_DISPATCH_TOKEN;
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
