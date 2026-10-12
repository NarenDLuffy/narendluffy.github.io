/**
 * One-off: run the real merge against the live 3GPP sync mirror, as the app
 * would during the meeting week. Not part of the build — run by hand:
 *   bun run scripts/check-draft-merge-live.ts
 */
import { readFileSync } from "node:fs";
import { mergeLive, SYNC_DRAFTS_BASE } from "../src/services/draftLiveSource";
import { walkListing } from "../src/lib/listingParser";

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36";

const raw = JSON.parse(readFileSync("public/data/meetings.json", "utf8"));
const meetings = Array.isArray(raw) ? raw : (raw.meetings ?? []);
const meeting = meetings.find((m: { slug: string }) => m.slug === "ran1-126-bis");
if (!meeting) throw new Error("meeting not found");

const index = JSON.parse(
  readFileSync("public/data/meetings/ran1-126-bis/drafts.json", "utf8"),
);

const fetchText = async (url: string): Promise<string | null> => {
  try {
    const res = await fetch(url, {
      headers: { accept: "text/html,*/*", "user-agent": UA },
      cache: "no-store",
    });
    return res.ok ? await res.text() : null;
  } catch {
    return null;
  }
};

console.log("crawling", SYNC_DRAFTS_BASE);
const crawl = await walkListing(SYNC_DRAFTS_BASE, fetchText, {
  maxDepth: 12,
  maxRequests: 200,
});
if (!crawl) {
  console.log("sync mirror did not answer — nothing to check");
  process.exit(0);
}
console.log(
  `live tree: ${crawl.folders.length} folders, ${crawl.files.length} files, ` +
    `${crawl.readFolders.length} folders read`,
);

const DAY = 86_400_000;
const start = Date.parse(`${meeting.startDate}T00:00:00Z`);
const cutoff = Number.isNaN(start) ? "" : new Date(start - 14 * DAY).toISOString();
const fresh = { ...crawl, files: crawl.files.filter((f) => !f.modifiedAt || f.modifiedAt >= cutoff) };
console.log(`after the 14-day cutoff: ${fresh.files.length} files`);

const agendaCodes = new Set(
  index.artifacts.map((a: { agendaItemId?: string | null }) => a.agendaItemId).filter(Boolean),
);
const { index: merged, freshCount, hiddenCount } = mergeLive(index, fresh, {
  meetingId: meeting.id,
  sourceType: "public",
  baseUrl: SYNC_DRAFTS_BASE,
  agendaCodes,
  reconcile: true,
});

console.log(`snapshot ${index.artifacts.length} files -> merged ${merged.artifacts.length}`);
console.log(`new ${freshCount}, hidden ${hiddenCount}`);

const hidden = merged.artifacts.filter((a: { removedAt?: string | null }) => a.removedAt);
const byFolder = new Map<string, number>();
hidden.forEach((a: { folderPath?: string | null }) => {
  const k = a.folderPath ?? "(root)";
  byFolder.set(k, (byFolder.get(k) ?? 0) + 1);
});
console.log("\nhidden by folder:");
[...byFolder.entries()].sort((a, b) => b[1] - a[1]).forEach(([k, v]) => console.log(`  ${v}  ${k}`));

const round1 = hidden.filter((a: { normalizedPath: string }) =>
  a.normalizedPath.includes("10.8.1") && a.normalizedPath.includes("round 1"),
);
console.log(`\n10.8.1 Round 1 files hidden: ${round1.length}`);
round1.forEach((a: { normalizedPath: string }) => console.log(`  ${a.normalizedPath}`));

const dupes = new Map<string, number>();
merged.artifacts.forEach((a: { folderPath?: string | null; filename: string }) => {
  const k = `${a.folderPath ?? ""}::${a.filename.toLowerCase()}`;
  dupes.set(k, (dupes.get(k) ?? 0) + 1);
});
const doubled = [...dupes.entries()].filter(([, n]) => n > 1);
console.log(`\nduplicate files: ${doubled.length}`);
doubled.slice(0, 10).forEach(([k]) => console.log(`  ${k}`));

const inRound1 = merged.artifacts
  .filter(
    (a: { folderPath?: string | null; removedAt?: string | null }) =>
      (a.folderPath ?? "").includes("10.8.1") &&
      (a.folderPath ?? "").includes("round 1") &&
      !a.removedAt,
  )
  .sort(
    (a: { modifiedAt?: string | null }, b: { modifiedAt?: string | null }) =>
      (a.modifiedAt ?? "").localeCompare(b.modifiedAt ?? ""),
  );
console.log(`\n10.8.1 Round 1 after the merge: ${inRound1.length} file(s)`);
inRound1.forEach((a: { filename: string; modifiedAt?: string | null; sources: unknown[] }) =>
  console.log(`  ${a.modifiedAt ?? "no date"}  ${a.filename}  (${a.sources.length} server(s))`),
);
