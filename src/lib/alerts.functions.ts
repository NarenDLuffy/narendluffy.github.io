import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

/**
 * Company "colleague needed" alerts. Same access model as presence: rows are
 * only returned to callers presenting the same company code. Alerts expire
 * after 10 minutes; dismissal is per device and never touches the server.
 */

export interface CompanyAlert {
  id: string;
  targetName: string;
  roomId: string;
  roomLabel?: string;
  senderId: string;
  senderName?: string;
  createdAt: string;
  expiresAt: string;
}

export const listCompanyAlerts = createServerFn({ method: "POST" })
  .inputValidator((data: unknown) =>
    z.object({ groupCode: z.string().min(1), meetingId: z.string().min(1) }).parse(data),
  )
  .handler(async ({ data }): Promise<CompanyAlert[]> => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { groupKeyOf } = await import("./presence.server");
    const { data: rows, error } = await supabaseAdmin
      .from("company_alerts")
      .select("id, target_name, room_id, room_label, sender_id, sender_name, created_at, expires_at")
      .eq("group_key", await groupKeyOf(data.groupCode))
      .eq("meeting_id", data.meetingId)
      .gt("expires_at", new Date().toISOString())
      .order("created_at", { ascending: true });
    if (error) throw new Error(error.message);
    return (rows ?? []).map((r) => ({
      id: r.id,
      targetName: r.target_name,
      roomId: r.room_id,
      ...(r.room_label ? { roomLabel: r.room_label } : {}),
      senderId: r.sender_id,
      ...(r.sender_name ? { senderName: r.sender_name } : {}),
      createdAt: r.created_at,
      expiresAt: r.expires_at,
    }));
  });

export const sendCompanyAlert = createServerFn({ method: "POST" })
  .inputValidator((data: unknown) =>
    z
      .object({
        groupCode: z.string().min(1),
        meetingId: z.string().min(1),
        targetName: z.string().min(1).max(80),
        roomId: z.string().min(1).max(120),
        roomLabel: z.string().max(160).optional(),
        senderId: z.string().min(1).max(40),
        senderName: z.string().max(80).optional(),
      })
      .parse(data),
  )
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { groupKeyOf } = await import("./presence.server");
    const now = Date.now();
    const { error } = await supabaseAdmin.from("company_alerts").insert({
      group_key: await groupKeyOf(data.groupCode),
      meeting_id: data.meetingId,
      target_name: data.targetName,
      room_id: data.roomId,
      room_label: data.roomLabel ?? null,
      sender_id: data.senderId,
      sender_name: data.senderName ?? null,
      created_at: new Date(now).toISOString(),
      expires_at: new Date(now + 10 * 60_000).toISOString(),
    });
    if (error) throw new Error(error.message);
    return { ok: true };
  });

/** Only the sender can withdraw an alert for everyone. */
export const cancelCompanyAlert = createServerFn({ method: "POST" })
  .inputValidator((data: unknown) =>
    z
      .object({ groupCode: z.string().min(1), id: z.string().uuid(), senderId: z.string().min(1) })
      .parse(data),
  )
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { groupKeyOf } = await import("./presence.server");
    const { error } = await supabaseAdmin
      .from("company_alerts")
      .delete()
      .eq("group_key", await groupKeyOf(data.groupCode))
      .eq("id", data.id)
      .eq("sender_id", data.senderId);
    if (error) throw new Error(error.message);
    return { ok: true };
  });
