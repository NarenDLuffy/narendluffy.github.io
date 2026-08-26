import { createHash } from "crypto";

/**
 * The company code is never stored: only a salted hash of it, so a database
 * dump cannot reveal which company codes are in use.
 */
export function groupKeyOf(groupCode: string): string {
  return createHash("sha256").update(`ran1live:${groupCode}`).digest("hex");
}
