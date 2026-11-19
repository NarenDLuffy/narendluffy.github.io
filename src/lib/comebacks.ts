/**
 * RAN3 comebacks ("CB: # 2_R19PSCellinfo" in the chair notes). Each has a
 * Drafts folder "CB # 2_R19PSCellinfo"; it closes when the chair removes "CB:".
 * Mirrors ingestion/ran3_comebacks.py so live-crawled folders link the same way.
 */
export interface Comeback {
  name: string;
  agendaCode: string;
  status: "open" | "closed" | "removed";
  number?: string;
  folder?: string;
}

export function nameKey(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]/g, "").replace(/rel(?=\d)/g, "r");
}

const FOLDER_RE = /^\s*CB\s*#?\s*(?:(\d+)\s*_\s*)?(\S.*?)\s*$/i;

/** The comeback a "CB # n_Name" folder belongs to: name first, number breaks ties; unique only. */
export function matchComebackFolder(folderName: string, rows: Comeback[]): Comeback | null {
  if (!/^\s*CB\b/i.test(folderName)) return null;
  const m = FOLDER_RE.exec(folderName);
  if (!m) return null;
  const num = m[1];
  const key = nameKey(m[2] ?? "");
  let hits = rows.filter((r) => nameKey(r.name) === key);
  if (hits.length === 0 && num) hits = rows.filter((r) => nameKey(`${num}${r.name}`) === key);
  if (hits.length > 1 && num) {
    const byNum = hits.filter((r) => r.number === num);
    if (byNum.length) hits = byNum;
  }
  return hits.length === 1 ? (hits[0] ?? null) : null;
}

const ORDER = { open: 0, closed: 1, removed: 2 } as const;

/** Comebacks for the followed agenda codes (or their parents), open first. */
export function comebacksFor(rows: Comeback[], codes: string[]): Comeback[] {
  return rows
    .filter((r) => codes.some((c) => c === r.agendaCode || c.startsWith(`${r.agendaCode}.`) || r.agendaCode.startsWith(`${c}.`)))
    .sort((a, b) => ORDER[a.status] - ORDER[b.status] || a.agendaCode.localeCompare(b.agendaCode, undefined, { numeric: true }));
}
