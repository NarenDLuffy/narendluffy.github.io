import { createFileRoute, Link } from "@tanstack/react-router";
import type { ReactNode } from "react";

export const Route = createFileRoute("/help")({
  head: () => ({
    meta: [
      { title: "How to use RAN1 Live — guide for delegates" },
      {
        name: "description",
        content:
          "A short tour of RAN1 Live: live schedule, drafts tracker, my agenda, FL deadlines, rooms and room presence — no account needed.",
      },
      { property: "og:title", content: "How to use RAN1 Live" },
      {
        property: "og:description",
        content:
          "Everything RAN1 Live can do during meeting week, explained for delegates in two minutes.",
      },
      { property: "og:type", content: "article" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: HelpPage,
});

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-border p-4">
      <h2 className="mb-1.5 text-sm font-semibold tracking-tight">{title}</h2>
      <div className="space-y-2 text-sm leading-relaxed text-muted-foreground">{children}</div>
    </section>
  );
}

function HelpPage() {
  return (
    <article className="space-y-4">
      <header className="space-y-2">
        <h1 className="text-xl font-semibold tracking-tight">How to use RAN1 Live</h1>
        <p className="text-sm text-muted-foreground">
          No account, no install. Open it on your phone and add it to your home screen for a
          full-screen app (Safari: Share → Add to Home Screen; Chrome: ⋮ → Install).
        </p>
        <p className="rounded-md border border-border bg-secondary/50 p-3 text-xs text-muted-foreground">
          Unofficial tool. The schedule is generated automatically from 3GPP meeting documents and
          may contain errors — confirm against the chair notes before relying on a time or room.
        </p>
      </header>

      <div className="grid gap-3 md:grid-cols-2">
        <Section title="Now">
          <p>
            What is running this minute, in meeting-local time: session, room, agenda items and
            progress. Use it when you leave a session and need to know where to go next.
          </p>
          <ul className="list-disc space-y-1 pl-4">
            <li>
              A <strong>Refresh</strong> button reloads the latest published schedule right away and
              shows when it was last rebuilt.
            </li>
            <li>
              <strong>FL deadline badges</strong> appear here when a deadline you set is due soon.
            </li>
          </ul>
          <Link to="/" className="inline-block underline underline-offset-2">
            Open Now
          </Link>
        </Section>

        <Section title="Schedule">
          <p>
            The week as a grid, one column per parallel track, every day drawn 08:30–19:30. Coffee
            and lunch bands run full width.
          </p>
          <ul className="list-disc space-y-1 pl-4">
            <li>
              <strong>Room colours</strong>: every room has its own colour on the timetable, the
              Rooms tab and the room pages.
            </li>
            <li>
              Room names show the session label in brackets where the chairs' documents give one,
              e.g. "1.1 Himalaya (RAN1 Brk2)".
            </li>
            <li>
              <strong>Agenda filter</strong>: matching blocks are highlighted and the rest dimmed;
              tick "Hide others" to hide them completely. Breaks always stay visible.
            </li>
            <li>
              <strong>Tap a block</strong> for the full agenda titles (e.g. "10.5.5 — Other physical
              channels and signals") with the per-item minute breakdown.
            </li>
            <li>
              A <strong>Refresh</strong> button pulls the newest schedule immediately and shows when
              it was last rebuilt.
            </li>
          </ul>
          <Link to="/schedule" className="inline-block underline underline-offset-2">
            Open Schedule
          </Link>
        </Section>

        <Section title="My agenda">
          <p>
            Everything you starred, in time order, plus <strong>Export .ics</strong> to drop your
            personal week into Outlook, Google or Apple Calendar.
          </p>
          <ul className="list-disc space-y-1 pl-4">
            <li>
              Exported times use the <strong>meeting city's time zone</strong> (daylight-saving
              handled), so 09:00 in Prague shows as 09:00 in Prague in your calendar.
            </li>
            <li>
              Events include the room with its session label, full agenda names, and 30-minute
              alarms for any FL deadlines you set.
            </li>
          </ul>
          <Link to="/agenda" className="inline-block underline underline-offset-2">
            Open My agenda
          </Link>
        </Section>

        <Section title="FL deadlines">
          <p>
            Add a deadline yourself per agenda item — tap <strong>Deadline</strong> in the block
            details sheet (e.g. "FL summary #1 due Tue 18:00").
          </p>
          <ul className="list-disc space-y-1 pl-4">
            <li>
              Reminders show as a badge on <strong>Now</strong> and as calendar alarms in the .ics
              export.
            </li>
            <li>
              The RAN1 email reflector is members-only behind an ETSI login, so deadlines cannot be
              read automatically — they are manual and stay on your own device.
            </li>
          </ul>
        </Section>

        <Section title="Drafts">
          <p>
            Live tracking of working documents. The tree mirrors the real <code>Inbox/</code>{" "}
            directory as discovered on the server, so it works for any meeting.
          </p>
          <ul className="list-disc space-y-1 pl-4">
            <li>
              <strong>All activity</strong> — every new or updated file.
            </li>
            <li>
              <strong>My items</strong> — only agenda items you bookmarked or followed.
            </li>
            <li>Unread counts appear on the tab and each folder; opening clears them.</li>
            <li>
              Source line shows where data came from: <strong>Venue</strong> (10.10.10.10, on
              meeting Wi-Fi), <strong>Sync</strong> (3GPP SYNC mirror) or <strong>Published</strong>{" "}
              (last built snapshot). Duplicates across servers are merged.
            </li>
            <li>
              It re-checks about every 60 s; <strong>Refresh now</strong> forces an immediate scan
              and reports how many files were new or updated.
            </li>
          </ul>
          <Link to="/drafts" className="inline-block underline underline-offset-2">
            Open Drafts
          </Link>
        </Section>

        <Section title="Rooms">
          <p>
            Only the rooms in use at the current meeting, each with its own colour and session
            label. Open a room to see its whole day, plus who from your group is currently checked
            in.
          </p>
          <Link to="/rooms" className="inline-block underline underline-offset-2">
            Open Rooms
          </Link>
        </Section>

        <Section title="Company (optional)">
          <p>
            Voluntary, account-free presence with colleagues: pick a shared group code, set a
            display name, check in to a room. It expires after two hours, is scoped to one meeting
            and never uses your location.
          </p>
          <Link to="/company" className="inline-block underline underline-offset-2">
            Open Company
          </Link>
        </Section>

        <Section title="Changes">
          <p>
            A diff feed: sessions that moved, rooms that changed, agenda items added or dropped
            since the previous version of the schedule documents.
          </p>
          <Link to="/changes" className="inline-block underline underline-offset-2">
            Open Changes
          </Link>
        </Section>

        <Section title="Meetings">
          <p>
            Switch meetings. Meetings are discovered from the official 3GPP portal, so past meetings
            stay browsable and the next one appears automatically — the current meeting is selected
            for you.
          </p>
          <Link to="/meetings" className="inline-block underline underline-offset-2">
            Open Meetings
          </Link>
        </Section>
      </div>

      <Section title="Good to know">
        <ul className="list-disc space-y-1 pl-4">
          <li>
            <strong>Keeping up to date:</strong> the schedule and drafts are rebuilt from the newest
            3GPP documents every 5 minutes during meeting hours, so new room names, session labels
            and document revisions appear on their own — no reinstall, no republish. Tap{" "}
            <strong>Refresh</strong> to pull the latest immediately.
          </li>
          <li>
            <strong>Offline:</strong> the last loaded schedule is cached, so it still opens in a
            basement room with no signal. A banner tells you the data is stale.
          </li>
          <li>
            <strong>Your data:</strong> bookmarks, follows, read state, deadlines, display name and
            presence stay in your own browser storage. Clearing site data resets them.
          </li>
          <li>
            <strong>Times</strong> are always shown in the meeting's local time zone.
          </li>
          <li>
            <strong>Venue mode</strong> (direct reading of the 10.10.10.10 meeting-local server) is
            currently switched off; drafts and the schedule come from the public 3GPP meeting-sync
            source. The code is kept for the future if the venue server supports HTTPS.
          </li>
          <li>
            <strong>Limitation:</strong> changes announced verbally in the room only appear once an
            updated document is uploaded.
          </li>
        </ul>
      </Section>
    </article>
  );
}
