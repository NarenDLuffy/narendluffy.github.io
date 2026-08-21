/**
 * Topic colouring.
 *
 * Topic keys are discovered per meeting, so no list of topics may be hard
 * coded. A stable hash maps whatever key the ingestion produced onto the
 * palette defined in styles.css.
 */

const PALETTE_SIZE = 8;

function hash(text: string): number {
  let h = 0;
  for (let i = 0; i < text.length; i += 1) {
    h = (h * 31 + text.charCodeAt(i)) >>> 0;
  }
  return h;
}

export function topicColor(topicKey: string): string {
  if (!topicKey) return "var(--topic-0)";
  if (topicKey === "break" || topicKey === "lunch") return "var(--muted-foreground)";
  return `var(--topic-${hash(topicKey) % PALETTE_SIZE})`;
}

export function topicStyle(topicKey: string): React.CSSProperties {
  return { ["--topic-color" as string]: topicColor(topicKey) };
}
