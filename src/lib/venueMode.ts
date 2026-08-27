/**
 * Venue mode.
 *
 * The meeting-room server lives at http://10.10.10.10/. Two independent facts
 * decide whether it can be read:
 *
 *   1. reachability — only devices on the meeting Wi-Fi have a route to it, so
 *      no server-side proxy anywhere can help; the fetch must come from the
 *      user's own browser, and
 *   2. scheme — a browser will not let an https:// page read an http:// URL
 *      (mixed content), and blocks it before any local-network prompt appears.
 *
 * So the venue path only works when the app itself is loaded over plain HTTP.
 * "Venue mode" is that HTTP twin of the same build: identical code, different
 * host, no extra software for anyone. This module owns detecting which side we
 * are on, hopping between them, and carrying device-local state across.
 */

const ALWAYS_KEY = "ran1live.venueMode.always.v1";
const DISMISS_KEY = "ran1live.venueMode.dismissed.v1";
const IMPORT_PARAM = "ran1import";

/** Hostname serving the plain-HTTP twin. Override per deployment if needed. */
export const VENUE_HOST: string =
  (import.meta.env['VITE_VENUE_HOST'] as string | undefined) ?? "venue.ran1.app";

/** Keys worth carrying over when switching hosts (all device-local, no PII). */
const TRANSFER_PREFIX = "ran1live.";

export function isBrowser(): boolean {
  return typeof window !== "undefined";
}

/** True when the current page is served over plain HTTP (venue mode). */
export function inVenueMode(): boolean {
  if (!isBrowser()) return false;
  return window.location.protocol === "http:";
}

/**
 * True when this page can never read the venue server because of the scheme.
 * Localhost is exempt: browsers allow http fetches from a local dev origin.
 */
export function venueBlockedByScheme(): boolean {
  if (!isBrowser()) return false;
  if (window.location.protocol !== "https:") return false;
  return !/^(localhost|127\.0\.0\.1)$/.test(window.location.hostname);
}

function collectLocalState(): Record<string, string> {
  const out: Record<string, string> = {};
  if (!isBrowser()) return out;
  try {
    for (let i = 0; i < window.localStorage.length; i += 1) {
      const key = window.localStorage.key(i);
      if (!key || !key.startsWith(TRANSFER_PREFIX)) continue;
      // Cached indexes are large and re-fetched anyway; only carry preferences.
      if (key.includes(".drafts.v1.")) continue;
      const value = window.localStorage.getItem(key);
      if (value != null && value.length < 20_000) out[key] = value;
    }
  } catch {
    /* storage unavailable */
  }
  return out;
}

function encodeState(state: Record<string, string>): string {
  const json = JSON.stringify(state);
  // btoa is latin1-only; encode UTF-8 first.
  return btoa(String.fromCharCode(...new TextEncoder().encode(json)));
}

function decodeState(encoded: string): Record<string, string> | null {
  try {
    const bytes = Uint8Array.from(atob(encoded), (c) => c.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes)) as Record<string, string>;
  } catch {
    return null;
  }
}

/** URL of the same route on the HTTP twin, carrying follows/bookmarks along. */
export function venueModeUrl(): string {
  if (!isBrowser()) return `http://${VENUE_HOST}/`;
  const url = new URL(window.location.href);
  url.protocol = "http:";
  url.host = VENUE_HOST;
  url.port = "";
  url.searchParams.set(IMPORT_PARAM, encodeState(collectLocalState()));
  return url.toString();
}

/** URL of the same route back on the secure host. */
export function secureModeUrl(secureHost: string): string {
  if (!isBrowser()) return `https://${secureHost}/`;
  const url = new URL(window.location.href);
  url.protocol = "https:";
  url.host = secureHost;
  url.searchParams.delete(IMPORT_PARAM);
  return url.toString();
}

/**
 * Apply state handed over by the other host, once, then clean the URL so the
 * blob never sticks around in history or in a shared link.
 */
export function consumeTransferredState(): boolean {
  if (!isBrowser()) return false;
  const url = new URL(window.location.href);
  const encoded = url.searchParams.get(IMPORT_PARAM);
  if (!encoded) return false;
  const state = decodeState(encoded);
  if (state) {
    for (const [key, value] of Object.entries(state)) {
      if (!key.startsWith(TRANSFER_PREFIX)) continue;
      try {
        if (window.localStorage.getItem(key) == null) window.localStorage.setItem(key, value);
      } catch {
        /* quota */
      }
    }
  }
  url.searchParams.delete(IMPORT_PARAM);
  window.history.replaceState(null, "", url.toString());
  return Boolean(state);
}

export function alwaysSwitch(): boolean {
  if (!isBrowser()) return false;
  try {
    return window.localStorage.getItem(ALWAYS_KEY) === "1";
  } catch {
    return false;
  }
}

export function setAlwaysSwitch(value: boolean): void {
  if (!isBrowser()) return;
  try {
    window.localStorage.setItem(ALWAYS_KEY, value ? "1" : "0");
  } catch {
    /* storage unavailable */
  }
}

export function venueBannerDismissed(): boolean {
  if (!isBrowser()) return false;
  try {
    return window.sessionStorage.getItem(DISMISS_KEY) === "1";
  } catch {
    return false;
  }
}

export function dismissVenueBanner(): void {
  if (!isBrowser()) return;
  try {
    window.sessionStorage.setItem(DISMISS_KEY, "1");
  } catch {
    /* storage unavailable */
  }
}

/** Navigate to the HTTP twin, remembering the choice when asked. */
export function switchToVenueMode(remember = false): void {
  if (!isBrowser()) return;
  if (remember) setAlwaysSwitch(true);
  window.location.assign(venueModeUrl());
}
