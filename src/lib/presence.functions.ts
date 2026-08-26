import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

/**
 * Shared company presence.
 *
 * The company code never leaves the browser in clear text beyond this call and
 * is never stored: the server hashes it into a group key, and rows are only
 * ever returned to a caller presenting the exact same code. The table itself is
 * unreachable from the browser (no anon grant, SELECT policy denies all), so
 * presence can only be read through these functions.
 */

const presenceRow = z.object({
  userId: z.string(),
  meetingId: z.string(),
  roomId: z.string(),
  sessionId: z.string().optional(),
  displayName: z.string().optional(),
  updatedAt: z.string(),
  expiresAt: z.string(),
});

export type RemotePresenceRow = z.infer<typeof presenceRow>;

async function groupKeyOf(groupCode: string): Promise<string> {
  const { createHash } = await import("crypto");
  return createHash("sha256").update(`ran1live:${groupCode}`).digest("hex");
}

export const listRemotePresence = createServerFn({ method: "POST" })
  .inputValidator((data: unknown) =>
    z.object({ groupCode: z.string().min(1), meetingId: z.string().min(1) }).parse(data),
  )
  .handler(async ({ data }): Promise<RemotePresenceRow[]> => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { data: rows, error } = await supabaseAdmin
      .from("company_presence")
      .select("user_id, meeting_id, room_id, session_id, display_name, updated_at, expires_at")
      .eq("group_key", await groupKeyOf(data.groupCode))
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
    const { error } = await supabaseAdmin.from("company_presence").upsert(
      {
        group_key: await groupKeyOf(data.groupCode),
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
    const { error } = await supabaseAdmin
      .from("company_presence")
      .delete()
      .eq("group_key", await groupKeyOf(data.groupCode))
      .eq("user_id", data.userId)
      .eq("meeting_id", data.meetingId);
    if (error) throw new Error(error.message);
    return { ok: true };
  });
