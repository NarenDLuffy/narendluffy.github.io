import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

/**
 * Shared per-meeting settings. The remote FTP host (e.g. RAN-Maastricht.3gpp.org)
 * is the same for every delegate, so the first person to enter it sets it for
 * everyone; later submissions never overwrite it.
 */

const HOST_RE = /^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$/i;

export const getMeetingFtpHost = createServerFn({ method: "POST" })
  .inputValidator((data: unknown) => z.object({ meetingId: z.string().min(1).max(80) }).parse(data))
  .handler(async ({ data }): Promise<string | null> => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { data: row } = await supabaseAdmin
      .from("meeting_settings")
      .select("remote_ftp_host")
      .eq("meeting_id", data.meetingId)
      .maybeSingle();
    return row?.remote_ftp_host ?? null;
  });

export const setMeetingFtpHost = createServerFn({ method: "POST" })
  .inputValidator((data: unknown) =>
    z
      .object({
        meetingId: z.string().min(1).max(80),
        host: z
          .string()
          .trim()
          .max(120)
          .transform((h) => h.replace(/^(s?ftp:\/\/)/i, "").replace(/\/.*$/, "").toLowerCase())
          .refine((h) => HOST_RE.test(h), "Not a valid host name"),
      })
      .parse(data),
  )
  .handler(async ({ data }): Promise<string> => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { data: existing } = await supabaseAdmin
      .from("meeting_settings")
      .select("remote_ftp_host")
      .eq("meeting_id", data.meetingId)
      .maybeSingle();
    if (existing?.remote_ftp_host) return existing.remote_ftp_host;
    const { error } = await supabaseAdmin
      .from("meeting_settings")
      .upsert({ meeting_id: data.meetingId, remote_ftp_host: data.host, updated_at: new Date().toISOString() });
    if (error) throw new Error(error.message);
    return data.host;
  });
