#!/usr/bin/env node
/**
 * Meeting-week health assertion.
 *
 * Reads the health record the refresh jobs write for each meeting
 * (public/data/meetings/<slug>/health.json) and fails when the meeting people
 * are actually using is being served stale or incomplete data.
 *
 * Why this exists: every optional source fails silently by design — a missing
 * remote-server address, an unreachable mirror, a timetable still built from a
 * Draft — and the site keeps serving the last good data. Without this check, a
 * skipped source looks exactly like a healthy run.
 *
 * Usage:
 *   node scripts/check-meeting-health.mjs                  # the active meeting
 *   node scripts/check-meeting-health.mjs --slug ran1-126-bis
 *   HEALTH_MAX_AGE_HOURS=3 node scripts/check-meeting-health.mjs
 *
 * Exit 0 = healthy (notes may be printed), 1 = a real problem to fix.
 */
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = process.cwd();
const DATA = join(ROOT, "public", "data");
// Tight during meeting-week session hours (weekdays 05–19 UTC covers Asian,
// European and US venues), looser otherwise. An 8-hour silent gap must fail.
function maxAgeHours(meeting) {
  if (process.env.HEALTH_MAX_AGE_HOURS) return Number(process.env.HEALTH_MAX_AGE_HOURS);
  const now = new Date();
  const sessionHours = now.getUTCDay() >= 1 && now.getUTCDay() <= 5 && now.getUTCHours() >= 5 && now.getUTCHours() < 19;
  return meeting?.status === "active" && sessionHours ? 2 : 6;
}

function arg(name) {
  const i = process.argv.indexOf(name);
  return i > -1 ? process.argv[i + 1] : null;
}

function readJson(path) {
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return null;
  }
}

const failures = [];
const notes = [];

const registry = readJson(join(DATA, "meetings.json")) ?? { meetings: [] };
const wanted = arg("--slug");
const meetings = registry.meetings ?? [];
const meeting = wanted
  ? meetings.find((m) => m.slug === wanted)
  : meetings.find((m) => m.status === "active");

if (!meeting) {
  console.log(
    wanted
      ? `no meeting named ${wanted} in meetings.json`
      : "no meeting is active — nothing has to be kept fresh right now"
  );
  process.exit(0);
}

const MAX_AGE_HOURS = maxAgeHours(meeting);
const stale = [];
const health = readJson(join(DATA, "meetings", meeting.slug, "health.json"));
if (!health) {
  failures.push("no health record — the refresh jobs have not reported for this meeting");
} else {
  const ageHours = (iso) => (iso ? (Date.now() - new Date(iso).getTime()) / 3.6e6 : null);
  for (const section of ["schedule", "drafts"]) {
    const rec = health[section];
    if (!rec) {
      failures.push(`the health record has no "${section}" section`);
      continue;
    }
    const age = ageHours(rec.lastSuccessAt);
    if (age === null) failures.push(`${section}: no last-success time`);
    else if (age > MAX_AGE_HOURS) {
      stale.push(section);
      failures.push(
        `${section}: last success ${Math.round(age)} h ago (limit ${MAX_AGE_HOURS} h)`
      );
    }
    if (rec.state && rec.state !== "ok") failures.push(`${section}: state "${rec.state}"`);
  }
  const remote = health.remoteFtp ?? {};
  if (remote.state === "read" || remote.state === "detected")
    notes.push(`remote meeting server ${remote.host} is being read`);
  for (const w of health.warnings ?? []) {
    if (w.level === "warn") failures.push(w.text);
    else notes.push(w.text);
  }
}

console.log(`health check — ${meeting.name} (${meeting.slug})`);
for (const n of notes) console.log(`  note: ${n}`);
for (const f of failures) console.error(`  FAIL: ${f}`);
if (process.env.GITHUB_OUTPUT && stale.length) {
  const { appendFileSync } = await import("node:fs");
  appendFileSync(process.env.GITHUB_OUTPUT, `stale=${stale.join(",")}\n`);
}
if (failures.length) {
  console.error(`\n${failures.length} problem(s) with the ${meeting.slug} data`);
  process.exit(1);
}
console.log("  healthy");
