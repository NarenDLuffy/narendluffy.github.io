/**
 * Checks for the live drafts merge: one upload stays one file, and a file the
 * meeting server no longer holds stops showing during the meeting week.
 *
 * Run with: bun run scripts/check-draft-merge.ts
 */
import {
  draftsTreeUrl,
  mergeLive,
  SYNC_DRAFTS_BASE,
  VENUE_DRAFTS_BASE,
  VENUE_DRAFTS_BASE_HTTPS,
} from "../src/services/draftLiveSource";
import { walkListing } from "../src/lib/listingParser";
import type { DraftIndex } from "../src/types/drafts";

let failures = 0;
const check = (name: string, ok: boolean, detail = "") => {
  if (ok) console.log(`  ok   ${name}`);
  else {
    failures += 1;
    console.log(`  FAIL ${name}${detail ? ` — ${detail}` : ""}`);
  }
};

const folder = (path: string, agendaItemId: string | null = null) => ({
  id: `f_${path}`,
  meetingId: "m",
  name: path.split("/").pop() ?? path,
  normalizedPath: path,
  sourceType: "public" as const,
  firstSeenAt: "2026-10-01T00:00:00.000Z",
  lastSeenAt: "2026-10-01T00:00:00.000Z",
  agendaItemId,
  agendaConfidence: 0.9,
  agendaMethod: "test",
  parentPath: path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : null,
  depth: path.split("/").length - 1,
  folderType: "generic" as const,
  classificationConfidence: 0.9,
  fileCount: 0,
  subtreeFileCount: 0,
});

const artifact = (path: string, filename: string) => ({
  id: `a_${path}_${filename}`,
  meetingId: "m",
  folderId: `f_${path}`,
  filename,
  normalizedPath: path ? `${path}/${filename}` : filename,
  fileType: "generic_draft" as const,
  classificationConfidence: 0.9,
  documentKey: `${path}::${filename}`,
  firstSeenAt: "2026-10-01T00:00:00.000Z",
  lastSeenAt: "2026-10-01T00:00:00.000Z",
  folderPath: path,
  sources: [
    {
      sourceType: "public" as const,
      sourcePath: path ? `${path}/${filename}` : filename,
      firstSeenAt: "2026-10-01T00:00:00.000Z",
      lastSeenAt: "2026-10-01T00:00:00.000Z",
    },
  ],
  revisions: [],
});

const snapshot = (
  artifacts: ReturnType<typeof artifact>[],
  folderPaths: string[],
  events: DraftIndex["events"] = [],
): DraftIndex => ({
  schemaVersion: 1,
  meetingId: "m",
  generatedAt: "2026-10-01T00:00:00.000Z",
  scanState: "ok",
  monitoring: true,
  unmappedFolders: [],
  folders: folderPaths.map((p) => folder(p)),
  artifacts,
  events,
});

const round = "10.8 (isac)/10.8.1 (evaluations)/round 1";
const liveFile = (folderPath: string, name: string) => ({
  path: folderPath ? `${folderPath}/${name}` : name,
  folderPath,
  name,
  url: `https://example.org/${encodeURIComponent(name)}`,
});

const meta = {
  meetingId: "m",
  sourceType: "public" as const,
  baseUrl: SYNC_DRAFTS_BASE,
  agendaCodes: new Set(["10.8", "10.8.1"]),
};

/* 1 — the probe roots all point at the drafts tree */
check("venue base is the drafts tree", VENUE_DRAFTS_BASE.endsWith("/Inbox/drafts/"));
check("venue HTTPS base is the drafts tree", VENUE_DRAFTS_BASE_HTTPS.endsWith("/Inbox/drafts/"));
check("sync base is the drafts tree", SYNC_DRAFTS_BASE.endsWith("/Inbox/drafts/"));
check(
  "a configured Inbox root is sent into drafts/",
  draftsTreeUrl("https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN1/Inbox/") ===
    "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN1/Inbox/drafts/",
);
check(
  "a drafts root is left alone",
  draftsTreeUrl("https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN1/Inbox/drafts/") ===
    "https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN1/Inbox/drafts/",
);

/* 2 — one upload on two servers stays one file, whatever root each used */
{
  const published = snapshot([artifact(round, "R1-2600001.docx")], [round]);
  const merged = mergeLive(
    published,
    {
      folders: [{ path: `drafts/${round}`, name: "round 1", parent: "drafts", depth: 4, url: "" }],
      files: [liveFile(`drafts/${round}`, "R1-2600001.docx")],
      readFolders: ["", "drafts", `drafts/${round}`],
    },
    { ...meta, reconcile: true },
  );
  check(
    "the same file under a different root is not duplicated",
    merged.index.artifacts.length === 1,
    `got ${merged.index.artifacts.length}`,
  );
  check("the same file under a different root is not announced as new", merged.freshCount === 0);
  check("nothing is hidden by a merge that lists it", merged.hiddenCount === 0);
}

/* 3 — a file the live crawl's folder did not list is hidden for the week */
{
  const published = snapshot(
    [artifact(round, "R1-2600001.docx"), artifact(round, "R1-2599999.docx")],
    [round],
  );
  const merged = mergeLive(
    published,
    {
      folders: [{ path: round, name: "round 1", parent: "10.8 (isac)", depth: 3, url: "" }],
      files: [liveFile(round, "R1-2600001.docx")],
      readFolders: ["", "10.8 (isac)", "10.8 (isac)/10.8.1 (evaluations)", round],
    },
    { ...meta, reconcile: true },
  );
  check("a withdrawn file is hidden", merged.hiddenCount === 1, `got ${merged.hiddenCount}`);
  check(
    "the withdrawn file is marked, not deleted",
    merged.index.artifacts.find((a) => a.filename === "R1-2599999.docx")?.removedAt != null,
  );
  check(
    "the listed file is untouched",
    merged.index.artifacts.find((a) => a.filename === "R1-2600001.docx")?.removedAt == null,
  );
}

/* 4 — a folder the crawl never opened says nothing: its files stay */
{
  const published = snapshot([artifact(round, "R1-2600001.docx")], [round]);
  const merged = mergeLive(
    published,
    {
      folders: [],
      files: [liveFile("10.8 (isac)", "notes.docx")],
      readFolders: ["", "10.8 (isac)"],
    },
    { ...meta, reconcile: true },
  );
  check("a file in a folder that was never read stays", merged.hiddenCount === 0);
  check(
    "and it stays visible",
    merged.index.artifacts.find((a) => a.filename === "R1-2600001.docx")?.removedAt == null,
  );
}

/* 5 — outside the meeting week nothing is hidden */
{
  const published = snapshot([artifact(round, "R1-2600001.docx")], [round]);
  const merged = mergeLive(
    published,
    { folders: [], files: [liveFile("10.8 (isac)", "notes.docx")], readFolders: ["", "10.8 (isac)"] },
    meta,
  );
  check("without a live week nothing is hidden", merged.hiddenCount === 0);
  check(
    "and the snapshot file stays visible",
    merged.index.artifacts.find((a) => a.filename === "R1-2600001.docx")?.removedAt == null,
  );
}

/* 6 — the crawler reports which folders it really opened */
{
  const pages: Record<string, string> = {
    "https://x/": `<table>
      <tr><td><a href="drafts/" class="dir">drafts</a></td></tr>
      <tr><td><a href="R1-1.zip" class="file">R1-1.zip</a></td></tr></table>`,
    "https://x/drafts/": `<table>
      <tr><td><a href="10.8%20(ISAC)/" class="dir">10.8 (ISAC)</a></td></tr></table>`,
    "https://x/drafts/10.8%20(ISAC)/": `<table>
      <tr><td><a href="R1-2.docx" class="file">R1-2.docx</a></td></tr></table>`,
  };
  const fetched = await walkListing(
    "https://x/",
    async (url) => pages[url] ?? null,
    { maxDepth: 10, maxRequests: 50 },
  );
  const read = fetched?.readFolders ?? [];
  check("the crawl root counts as read", read.includes(""));
  check(
    "a folder the crawler opened is recorded",
    read.includes("drafts/10.8 (isac)"),
    read.join(" | "),
  );
  check(
    "a folder it never reached is not recorded",
    !read.includes("drafts/10.8 (isac)/10.8.1 (evaluations)"),
  );
}

console.log(failures === 0 ? "\nall draft-merge checks passed" : `\n${failures} check(s) failed`);
if (failures > 0) process.exit(1);
