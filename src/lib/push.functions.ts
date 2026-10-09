import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

/**
 * Web Push subscriptions, scoped to the hashed company code — same access
 * model as presence and alerts: the table is service-role only.
 */

const subSchema = z.object({
  groupCode: z.string().min(1),
  userId: z.string().min(1).max(40),
  endpoint: z.string().url().max(2000),
  p256dh: z.string().min(1).max(200),
  auth: z.string().min(1).max(100),
});

export const subscribePush = createServerFn({ method: "POST" })
  .inputValidator((data: unknown) => subSchema.parse(data))
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { groupKeyOf } = await import("./presence.server");
    const { error } = await supabaseAdmin.from("push_subscriptions").upsert(
      {
        group_key: await groupKeyOf(data.groupCode),
        user_id: data.userId,
        endpoint: data.endpoint,
        p256dh: data.p256dh,
        auth: data.auth,
      },
      { onConflict: "endpoint" },
    );
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const unsubscribePush = createServerFn({ method: "POST" })
  .inputValidator((data: unknown) =>
    z.object({ groupCode: z.string().min(1), endpoint: z.string().url().max(2000) }).parse(data),
  )
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { groupKeyOf } = await import("./presence.server");
    const { error } = await supabaseAdmin
      .from("push_subscriptions")
      .delete()
      .eq("group_key", await groupKeyOf(data.groupCode))
      .eq("endpoint", data.endpoint);
    if (error) throw new Error(error.message);
    return { ok: true };
  });

/** Fan out a push to every subscribed device in the company group. */
export async function notifyGroupPush(
  groupKey: string,
  payload: { title: string; body: string; url: string; tag: string },
): Promise<void> {
  const priv = process.env["VAPID_PRIVATE_KEY"];
  if (!priv) return; // push not configured — banner still works
  const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
  const { sendWebPush } = await import("./push.server");
  const { VAPID_PUBLIC_KEY } = await import("./pushConfig");
  const { data: subs, error } = await supabaseAdmin
    .from("push_subscriptions")
    .select("endpoint, p256dh, auth")
    .eq("group_key", groupKey);
  if (error || !subs?.length) return;
  const vapid = { subject: "mailto:ran1live@ran1.app", privPkcs8: priv, pubRaw: VAPID_PUBLIC_KEY };
  const dead: string[] = [];
  await Promise.allSettled(
    subs.map(async (s) => {
      const ok = await sendWebPush(
        { endpoint: s.endpoint, p256dh: s.p256dh, auth: s.auth },
        JSON.stringify(payload),
        vapid,
      );
      if (!ok) dead.push(s.endpoint);
    }),
  );
  if (dead.length) {
    await supabaseAdmin.from("push_subscriptions").delete().in("endpoint", dead);
  }
}
