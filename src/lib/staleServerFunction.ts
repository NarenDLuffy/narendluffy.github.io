const STALE_RELOAD_KEY = "ran1live.staleReload";
const RELOAD_COOLDOWN_MS = 60_000;

/** An open tab can hold a server-function ID from before an app update/restart. */
export function isStaleServerFunctionError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error ?? "");
  return /Invalid server function ID|Server function info not found|server function|serverFn/i.test(
    message,
  );
}

/** Reload at most once a minute; after that, leave the normal error UI in place. */
export function reloadIfStaleServerFunction(error: unknown): boolean {
  if (typeof window === "undefined" || !isStaleServerFunctionError(error)) return false;
  try {
    const last = Number(window.sessionStorage.getItem(STALE_RELOAD_KEY) ?? 0);
    if (Date.now() - last < RELOAD_COOLDOWN_MS) return false;
    window.sessionStorage.setItem(STALE_RELOAD_KEY, String(Date.now()));
  } catch {
    return false;
  }
  window.location.reload();
  return true;
}
