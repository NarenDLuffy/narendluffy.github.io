import { useEffect, useState } from "react";
import { getMeetingFtpHost, setMeetingFtpHost } from "@/lib/meetingSettings.functions";
import { Button } from "@/components/ui/button";

const SKIP_KEY = "ran1live.ftpHostPrompt.skipped.";

/** Asks delegates once for the meeting's remote FTP host; first answer wins for everyone. */
export function RemoteFtpHostCard({ meetingId }: { meetingId: string }) {
  const [state, setState] = useState<"loading" | "ask" | "hidden">("loading");
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (window.localStorage.getItem(SKIP_KEY + meetingId) === "1") {
      setState("hidden");
      return;
    }
    getMeetingFtpHost({ data: { meetingId } })
      .then((h) => setState(h ? "hidden" : "ask"))
      .catch(() => setState("hidden"));
  }, [meetingId]);

  if (state !== "ask") return null;

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await setMeetingFtpHost({ data: { meetingId, host: value } });
      setState("hidden");
    } catch {
      setError("That doesn't look like a host name, e.g. RAN-Maastricht.3gpp.org");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-2 rounded-lg border border-border bg-card p-3 text-xs">
      <p className="font-medium text-foreground">Remote FTP host for this meeting?</p>
      <p className="text-muted-foreground">
        From the meeting invitation's "delegates not in the meeting rooms" FTP details (e.g.
        RAN-Maastricht.3gpp.org). Entered once for everyone — it keeps drafts and schedules fresh
        from outside the venue wifi.
      </p>
      <div className="flex gap-2">
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="RAN-City.3gpp.org"
          className="mono-code min-h-10 flex-1 rounded-md border border-input bg-background px-2 outline-none focus:ring-2 focus:ring-ring"
        />
        <Button size="sm" disabled={busy || !value.trim()} onClick={save}>
          Save
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            window.localStorage.setItem(SKIP_KEY + meetingId, "1");
            setState("hidden");
          }}
        >
          Skip
        </Button>
      </div>
      {error ? <p className="text-destructive">{error}</p> : null}
    </div>
  );
}
