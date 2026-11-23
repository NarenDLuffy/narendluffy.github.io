/**
 * RAN4 Drafts folders are named by moderator topic ("[121][201] NR_RRM_Ph6"),
 * not agenda number. topics.json (from the chair's List_Topics_moderators
 * workbook) maps a topic to its agenda items; the folder takes the first one.
 * Mirrors draft_tracker/update_drafts.py::_ran4_resolver.
 */
export type TopicMap = Record<string, string[]>;

const TOPIC_FOLDER_RE = /^\s*\[\d+(?:bis)?\]\s*\[(\d{3}(?:-[A-Z])?)\]/i;

/** undefined: not a topic folder; null: a topic folder without agenda items. */
export function topicFolderCode(segment: string, topics: TopicMap): string | null | undefined {
  const m = TOPIC_FOLDER_RE.exec(segment);
  if (!m?.[1]) return undefined;
  return topics[m[1].toUpperCase()]?.[0] ?? null;
}
