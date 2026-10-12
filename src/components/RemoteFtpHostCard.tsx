import { useEffect, useState } from "react";
import { getMeetingFtpHost, setMeetingFtpHost } from "@/lib/meetingSettings.functions";
import { Button } from "@/components/ui/button";

const SKIP_KEY = "ran1live.ftpHostPrompt.skipped.";

type State = "loading" | "ask" | "status" | "change" | "skipped";

/**
 * Shows the meeting's remote FTP host and lets delegates set or correct it.
 * First answer wins for passive entries; the Change form explicitly replaces
 * a stored host so a wrong address is never stuck.
 */
export function RemoteFtpHostCard({ meetingId }: { meetingId: string }) {
  const [state, setState] = useState<State>("loading");
  const [host, setHost] = useState<string | null>(null);
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const skipped = window.localStorage.getItem(SKIP_KEY + meetingId) === "1";
    getMeetingFtpHost({ data: { meetingId } })
      .then((h) => {
        setHost(h);
        setState(h ? "status" : skipped ? "skipped" : "ask");
      })
      .catch(() => setState("skipped"));
  }, [meetingId]);

  if (state === "loading") return null;

  const save = async (replace: boolean) => {
    setBusy(true);
    setError(null);
    try {
      const saved = await setMeetingFtpHost({ data: { meetingId, host: value, replace } });
      setHost(saved);
      setValue("");
      window.localStorage.removeItem(SKIP_KEY + meetingId);
      setState("status");
    } catch {
      setError("That doesn't look like a host name, e.g. RAN-Maastricht.3gpp.org");
    } finally {
      setBusy(false);
    }
  };

  const form = (replace: boolean) => (
    <div className="flex gap-2">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="RAN-City.3gpp.org"
        className="mono-code min-h-10 flex-1 rounded-md border border-input bg-background px-2 outline-none focus:ring-2 focus:ring-ring"
      />
      <Button size="sm" disabled={busy || !value.trim()} onClick={() => save(replace)}>
        Save
      </Button>
      {replace ? (
        <Button size="sm" variant="ghost" onClick={() => setState("status")}>
          Cancel
        </Button>
      ) : (
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            window.localStorage.setItem(SKIP_KEY + meetingId, "1");
            setState("skipped");
          }}
        >
          Skip
        </Button>
      )}
    </div>
  );

  if (state === "status" && host) {
    return (
      <div className="flex items-center justify-between gap-2 rounded-lg border border-border bg-card px-3 py-2 text-xs">
        <p className="text-muted-foreground">
          Remote server: <span className="mono-code font-medium text-foreground">{host}</span>
        </p>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            setValue(host);
            setError(null);
            setState("change");
          }}
        >
          Change
        </Button>
      </div>
    );
  }

  if (state === "change") {
    return (
      <div className="space-y-2 rounded-lg border border-border bg-card p-3 text-xs">
        <p className="font-medium text-foreground">Change the remote FTP host</p>
        <p className="text-muted-foreground">
          Replaces the stored address for everyone — use this if the first entry was wrong or the
          venue changed it.
        </p>
        {form(true)}
        {error ? <p className="text-destructive">{error}</p> : null}
      </div>
    );
  }

  if (state === "skipped") {
    return (
      <div className="flex items-center justify-between gap-2 rounded-lg border border-border bg-card px-3 py-2 text-xs">
        <p className="text-muted-foreground">Remote server: not set</p>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            window.localStorage.removeItem(SKIP_KEY + meetingId);
            setState("ask");
          }}
        >
          Set remote server
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-2 rounded-lg border border-border bg-card p-3 text-xs">
      <p className="font-medium text-foreground">Remote FTP host for this meeting?</p>
      <p className="text-muted-foreground">
        From the meeting invitation's "delegates not in the meeting rooms" FTP details (e.g.
        RAN-Maastricht.3gpp.org). Entered once for everyone — it keeps drafts and schedules fresh
        from outside the venue wifi.
      </p>
      {form(false)}
      {error ? <p className="text-destructive">{error}</p> : null}
    </div>
  );
}
