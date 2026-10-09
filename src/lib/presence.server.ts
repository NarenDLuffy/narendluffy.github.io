/**
 * The company code is never stored: only a salted hash of it, so a database
 * dump cannot reveal which company codes are in use. Uses Web Crypto so it
 * runs the same on the edge runtime as in dev.
 */
export async function groupKeyOf(groupCode: string): Promise<string> {
  const bytes = new TextEncoder().encode(`ran1live:${groupCode}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
