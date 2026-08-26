import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

/**
 * Shared company presence.
 *
 * Rows are only ever returned to a caller presenting the exact same company
 * code, which the server hashes into a group key. The table is unreachable
 * from the browser (no anon grant, SELECT policy denies all), so presence can
 * only be read through these functions.
 *
 * This file must stay a thin wrapper: server-function splitting removes any
 * runtime sibling declared at module scope. Helpers live in presence.server.ts.
 */

export interface RemotePresenceRow {
  userId: string;
  meetingId: string;
  roomId: string;
  sessionId?: string;
  displayName?: string;
  updatedAt: string;
  expiresAt: string;
}

export const listRemotePresence = createServerFn({ method: "POST" })
  .inputValidator((data: unknown) =>
    z.object({ groupCode: z.string().min(1), meetingId: z.string().min(1) }).parse(data),
  )
  .handler(async ({ data }): Promise<RemotePresenceRow[]> => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { groupKeyOf } = await import("./presence.server");
    const { data: rows, error } = await supabaseAdmin
      .from("company_presence")
      .select("user_id, meeting_id, room_id, session_id, display_name, updated_at, expires_at")
      .eq("group_key", groupKeyOf(data.groupCode))
      .eq("meeting_id", data.meetingId)
      .gt("expires_at", new Date().toISOString());
    if (error) throw new Error(error.message);
    return (rows ?? []).map((r) => ({
      userId: r.user_id,
      meetingId: r.meeting_id,
      roomId: r.room_id,
      ...(r.session_id ? { sessionId: r.session_id } : {}),
      ...(r.display_name ? { displayName: r.display_name } : {}),
      updatedAt: r.updated_at,
      expiresAt: r.expires_at,
    }));
  });

export const setRemotePresence = createServerFn({ method: "POST" })
  .inputValidator((data: unknown) =>
    z
      .object({
        groupCode: z.string().min(1),
        userId: z.string().min(1),
        meetingId: z.string().min(1),
        roomId: z.string().min(1),
        sessionId: z.string().optional(),
        displayName: z.string().max(80).optional(),
        expiresAt: z.string(),
      })
      .parse(data),
  )
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { groupKeyOf } = await import("./presence.server");
    const { error } = await supabaseAdmin.from("company_presence").upsert(
      {
        group_key: groupKeyOf(data.groupCode),
        user_id: data.userId,
        meeting_id: data.meetingId,
        room_id: data.roomId,
        session_id: data.sessionId ?? null,
        display_name: data.displayName ?? null,
        updated_at: new Date().toISOString(),
        expires_at: data.expiresAt,
      },
      { onConflict: "group_key,user_id,meeting_id" },
    );
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const clearRemotePresence = createServerFn({ method: "POST" })
  .inputValidator((data: unknown) =>
    z
      .object({
        groupCode: z.string().min(1),
        userId: z.string().min(1),
        meetingId: z.string().min(1),
      })
      .parse(data),
  )
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { groupKeyOf } = await import("./presence.server");
    const { error } = await supabaseAdmin
      .from("company_presence")
      .delete()
      .eq("group_key", groupKeyOf(data.groupCode))
      .eq("user_id", data.userId)
      .eq("meeting_id", data.meetingId);
    if (error) throw new Error(error.message);
    return { ok: true };
  });
