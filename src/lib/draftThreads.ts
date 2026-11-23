import type { DraftArtifact } from "@/types/drafts";

/**
 * Group draft files into discussion threads. 3GPP email-discussion drafts are
 * usually named "<title> - v<N>[.<M>]-<CompanyA>_<CompanyB>", where the last
 * company is whoever uploaded that version. Files without a version marker
 * form a thread of their own.
 */
export interface ThreadVersion {
  artifact: DraftArtifact;
  version: number[];
  author: string | null;
  at: string;
}
export interface DraftThread {
  key: string;
  title: string;
  isSummary: boolean;
  versions: ThreadVersion[]; // oldest first
  latest: ThreadVersion;
}

const VERSION_RE = /[\s_\-]*\(?v(?:er(?:sion)?)?[\s_.]*(\d+(?:[._]\d+)*)\)?/i;

export function parseDraftName(filename: string): {
  key: string;
  title: string;
  version: number[] | null;
  author: string | null;
} {
  const base = filename.replace(/\.[a-z0-9]{2,5}$/i, "");
  const m = VERSION_RE.exec(base);
  if (!m || m.index === 0) {
    const title = base.replace(/[_\s]+/g, " ").trim();
    return { key: title.toLowerCase(), title, version: null, author: null };
  }
  const head = base.slice(0, m.index);
  const tail = base.slice(m.index + m[0].length).replace(/^[\s_\-]+/, "");
  const companies = tail.split(/[_\-\s]+/).filter((s) => /[a-z]/i.test(s));
  const title = head.replace(/[_\s]+/g, " ").replace(/[\s\-]+$/, "").trim();
  return {
    key: title.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim(),
    title,
    version: (m[1] ?? "0").split(/[._]/).map(Number),
    author: companies.length ? companies[companies.length - 1]! : null,
  };
}

function cmp(a: number[], b: number[]) {
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const d = (a[i] ?? -1) - (b[i] ?? -1);
    if (d) return d;
  }
  return 0;
}

export function buildThreads(artifacts: DraftArtifact[]): DraftThread[] {
  const groups = new Map<string, { title: string; versions: ThreadVersion[]; summary: boolean }>();
  for (const a of artifacts) {
    if (a.removedAt) continue;
    const p = parseDraftName(a.filename);
    const key = `${a.folderPath ?? ""}|${p.key}`;
    const g = groups.get(key) ?? { title: p.title, versions: [], summary: false };
    g.versions.push({
      artifact: a,
      version: p.version ?? [0],
      author: p.author,
      at: a.modifiedAt ?? a.firstSeenAt,
    });
    if (a.fileType === "fl_summary" || /summary/i.test(p.title)) g.summary = true;
    groups.set(key, g);
  }
  const threads: DraftThread[] = [];
  for (const [key, g] of groups) {
    g.versions.sort((x, y) => cmp(x.version, y.version) || x.at.localeCompare(y.at));
    threads.push({ key, title: g.title, isSummary: g.summary, versions: g.versions, latest: g.versions[g.versions.length - 1]! });
  }
  return threads.sort((a, b) => b.latest.at.localeCompare(a.latest.at));
}
