import { createFileRoute } from "@tanstack/react-router";

// Read-only, non-private: returns only the public host name delegates entered
// for a meeting, so the GitHub refresh job knows which remote FTP to crawl.
export const Route = createFileRoute("/api/public/meeting-ftp-host")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        const meetingId = new URL(request.url).searchParams.get("meeting")?.slice(0, 80);
        if (!meetingId) return Response.json({ host: null }, { status: 400 });
        const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
        const { data } = await supabaseAdmin
          .from("meeting_settings")
          .select("remote_ftp_host")
          .eq("meeting_id", meetingId)
          .maybeSingle();
        return Response.json({ host: data?.remote_ftp_host ?? null });
      },
    },
  },
});
