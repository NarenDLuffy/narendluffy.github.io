import { createFileRoute, Link } from "@tanstack/react-router";
import type { ReactNode } from "react";

export const Route = createFileRoute("/help")({
  head: () => ({
    meta: [
      { title: "How to use RAN1 Live — guide for delegates" },
      {
        name: "description",
        content:
          "A short tour of RAN1 Live: live schedule, drafts tracker, my agenda, rooms and room presence — no account needed.",
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
          <Link to="/" className="inline-block underline underline-offset-2">
            Open Now
          </Link>
        </Section>

        <Section title="Schedule">
          <p>
            The week as a grid, one column per parallel track, every day drawn 08:30–19:30. Tap a
            block for the per-agenda-item minute breakdown. Coffee and lunch bands run full width.
            Search and agenda filters narrow the grid; the star adds a session to My agenda.
          </p>
          <Link to="/schedule" className="inline-block underline underline-offset-2">
            Open Schedule
          </Link>
        </Section>

        <Section title="My agenda">
          <p>
            Everything you starred, in time order, plus <strong>Export .ics</strong> to drop your
            personal week into Outlook, Google or Apple Calendar.
          </p>
          <Link to="/agenda" className="inline-block underline underline-offset-2">
            Open My agenda
          </Link>
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
            Every physical room in use and what is scheduled in it, plus who from your group is
            currently checked in.
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
            <strong>Offline:</strong> the last loaded schedule is cached, so it still opens in a
            basement room with no signal. A banner tells you the data is stale.
          </li>
          <li>
            <strong>Your data:</strong> bookmarks, follows, read state, display name and presence
            stay in your own browser storage. Clearing site data resets them.
          </li>
          <li>
            <strong>Times</strong> are always shown in the meeting's local time zone.
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
