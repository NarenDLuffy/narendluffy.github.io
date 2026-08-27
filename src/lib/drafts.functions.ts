import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

/**
 * Server-side crawl of the public 3GPP sync mirror, exposed to the browser.
 *
 * The browser is blocked from reading www.3gpp.org listings by CORS; the server
 * is not. This is the fallback path used whenever the venue server cannot be
 * reached (i.e. whenever the user is not sitting on the meeting-room network).
 *
 * Thin wrapper by design: server-function splitting removes runtime siblings
 * declared at module scope, so all logic lives in syncCrawl.server.ts.
 */

export const crawlSyncDrafts = createServerFn({ method: "POST" })
  .inputValidator((data: unknown) =>
    z
      .object({
        url: z
          .string()
          .url()
          .max(300)
          .refine(
            (u) => u.startsWith("https://www.3gpp.org/ftp/Meetings_3GPP_SYNC/RAN1/"),
            "url must be inside the public RAN1 sync tree",
          ),
      })
      .parse(data),
  )
  .handler(async ({ data }) => {
    const { crawlSync, isAllowedSyncUrl } = await import("./syncCrawl.server");
    if (!isAllowedSyncUrl(data.url)) throw new Error("Forbidden");
    const result = await crawlSync(data.url);
    return {
      ok: Boolean(result),
      folders: result?.folders ?? [],
      files: result?.files ?? [],
    };
  });
