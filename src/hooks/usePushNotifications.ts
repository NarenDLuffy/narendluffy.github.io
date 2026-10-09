import { useCallback, useEffect, useState } from "react";
import { PUSH_SW_PATH, VAPID_PUBLIC_KEY } from "@/lib/pushConfig";
import { subscribePush, unsubscribePush } from "@/lib/push.functions";
import { getIdentity } from "@/services/presenceService";

export type PushState =
  | "unsupported"
  | "preview"
  | "blocked"
  | "needsInstall"
  | "off"
  | "on"
  | "busy";

/** iOS only supports web push from an installed home-screen app. */
function isIosNotInstalled(): boolean {
  const ua = window.navigator.userAgent;
  const isIos = /iPad|iPhone|iPod/.test(ua) || (navigator.maxTouchPoints > 1 && /Mac/.test(ua));
  if (!isIos) return false;
  const standalone =
    window.matchMedia("(display-mode: standalone)").matches ||
    (window.navigator as { standalone?: boolean }).standalone === true;
  return !standalone;
}

function b64urlToBytes(s: string): Uint8Array {
  const pad = "=".repeat((4 - (s.length % 4)) % 4);
  const bin = atob((s + pad).replace(/-/g, "+").replace(/_/g, "/"));
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function isPreviewHost(): boolean {
  const h = window.location.hostname;
  return (
    h.startsWith("id-preview--") ||
    h.startsWith("preview--") ||
    h === "lovableproject.com" ||
    h.endsWith(".lovableproject.com") ||
    h.endsWith(".lovableproject-dev.com") ||
    h.endsWith(".beta.lovable.dev") ||
    h === "localhost"
  );
}

/**
 * Web Push subscription for "colleague needed" alerts. Production only —
 * never registers a service worker in the Lovable preview or dev.
 */
export function usePushNotifications() {
  const [state, setState] = useState<PushState>("busy");

  const detect = useCallback(async (): Promise<PushState> => {
    if (typeof window === "undefined") return "busy";
    if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window))
      return "unsupported";
    if (!import.meta.env.PROD || isPreviewHost()) return "preview";
    if (isIosNotInstalled()) return "needsInstall";
    if (Notification.permission === "denied") return "blocked";
    const reg = await navigator.serviceWorker.getRegistration(PUSH_SW_PATH);
    const sub = reg ? await reg.pushManager.getSubscription() : null;
    return sub ? "on" : "off";
  }, []);

  useEffect(() => {
    void detect().then(setState);
  }, [detect]);

  const enable = useCallback(async () => {
    setState("busy");
    try {
      const id = getIdentity();
      if (!id.groupId) throw new Error("Join your company group first.");
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setState(permission === "denied" ? "blocked" : "off");
        return;
      }
      await navigator.serviceWorker.register(PUSH_SW_PATH);
      // register() resolves before the worker is active; subscribing right
      // away fails with "no active service worker" on Android Chrome.
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: b64urlToBytes(VAPID_PUBLIC_KEY) as BufferSource,
      });
      const key = sub.getKey("p256dh");
      const auth = sub.getKey("auth");
      if (!key || !auth) throw new Error("Browser did not provide push keys.");
      const toB64url = (b: ArrayBuffer) =>
        btoa(String.fromCharCode(...new Uint8Array(b)))
          .replace(/\+/g, "-")
          .replace(/\//g, "_")
          .replace(/=+$/, "");
      await subscribePush({
        data: {
          groupCode: id.groupId,
          userId: id.userId,
          endpoint: sub.endpoint,
          p256dh: toB64url(key),
          auth: toB64url(auth),
        },
      });
      setState("on");
    } catch (e) {
      console.warn("push enable failed", e);
      setState("off");
      throw e;
    }
  }, []);

  const disable = useCallback(async () => {
    setState("busy");
    try {
      const id = getIdentity();
      const reg = await navigator.serviceWorker.getRegistration(PUSH_SW_PATH);
      const sub = reg ? await reg.pushManager.getSubscription() : null;
      if (sub) {
        await sub.unsubscribe();
        if (id.groupId) {
          await unsubscribePush({ data: { groupCode: id.groupId, endpoint: sub.endpoint } });
        }
      }
    } finally {
      setState("off");
    }
  }, []);

  return { state, enable, disable };
}
