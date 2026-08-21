const KNOWN = [
  "isac",
  "waveform",
  "aiot",
  "aiml",
  "mimo",
  "ntn",
  "maintenance",
] as const;

/** Returns the CSS variable holding the colour for a topic key. */
export function topicColor(topicKey: string): string {
  const key = (KNOWN as readonly string[]).includes(topicKey) ? topicKey : "default";
  return `var(--topic-${key})`;
}

export function topicStyle(topicKey: string): React.CSSProperties {
  return { ["--topic-color" as string]: topicColor(topicKey) };
}
