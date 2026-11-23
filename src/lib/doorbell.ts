import { supabase } from "@/integrations/supabase/client";

/**
 * Live "something changed" ping for one company group in one meeting. The
 * message carries no data — receivers just refetch through the normal server
 * functions — and the channel name is a hash, so the company code never
 * travels in the clear. Polling stays as a slow fallback.
 */
async function channelName(groupCode: string, meetingId: string) {
  const bytes = new TextEncoder().encode(`${groupCode.trim().toLowerCase()}|${meetingId}`);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return "bell-" + Array.from(new Uint8Array(hash).slice(0, 12), (b) => b.toString(16).padStart(2, "0")).join("");
}

type Ch = ReturnType<typeof supabase.channel>;
const open = new Map<string, { ch: Ch; listeners: Set<() => void>; ready: Promise<void> }>();

export function subscribeDoorbell(groupCode: string, meetingId: string, onRing: () => void) {
  let key = "";
  let closed = false;
  void channelName(groupCode, meetingId).then((name) => {
    if (closed) return;
    key = name;
    let entry = open.get(name);
    if (!entry) {
      const ch = supabase.channel(name, { config: { broadcast: { self: false } } });
      const listeners = new Set<() => void>();
      ch.on("broadcast", { event: "ring" }, () => listeners.forEach((l) => l()));
      const ready = new Promise<void>((res) => ch.subscribe((s) => s === "SUBSCRIBED" && res()));
      entry = { ch, listeners, ready };
      open.set(name, entry);
    }
    entry.listeners.add(onRing);
  });
  return () => {
    closed = true;
    const entry = key ? open.get(key) : undefined;
    if (!entry) return;
    entry.listeners.delete(onRing);
    if (entry.listeners.size === 0) {
      void supabase.removeChannel(entry.ch);
      open.delete(key);
    }
  };
}

export async function ringDoorbell(groupCode: string, meetingId: string) {
  try {
    const name = await channelName(groupCode, meetingId);
    const entry = open.get(name);
    if (entry) {
      await entry.ready;
      await entry.ch.send({ type: "broadcast", event: "ring", payload: {} });
      return;
    }
    const ch = supabase.channel(name);
    await new Promise<void>((res) => ch.subscribe((s) => s === "SUBSCRIBED" && res()));
    await ch.send({ type: "broadcast", event: "ring", payload: {} });
    void supabase.removeChannel(ch);
  } catch (e) {
    console.warn("doorbell failed", e);
  }
}
