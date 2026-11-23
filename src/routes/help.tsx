import { createFileRoute, Link } from "@tanstack/react-router";
import type { ReactNode } from "react";

export const Route = createFileRoute("/help")({
  head: () => ({
    meta: [
      { title: "How to use 3GPP Companion — RAN1–RAN4, SA1, SA2 and RAN Plenary guide" },
      {
        name: "description",
        content:
          "A short RAN1–RAN4, SA1, SA2 and RAN Plenary guide: schedules, drafts, my agenda, rooms and colleague presence — no account needed.",
      },
      { property: "og:title", content: "How to use 3GPP Companion for RAN Plenary, RAN1–RAN4, SA1 and SA2" },
      {
        property: "og:description",
        content:
          "How to follow a RAN Plenary, RAN1–RAN4, SA1 or SA2 meeting week with schedules, drafts, rooms and colleague alerts.",
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
        <h1 className="text-xl font-semibold tracking-tight">How to use 3GPP Companion</h1>
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
        <Section title="Light on the 3GPP servers">
          <p>
            Live Drafts folders are scanned once for everyone (about every 90 seconds) and shared,
            so more users do not mean more requests to 3GPP. Hidden tabs and locked phones do not
            refresh. Thanks to Duckhyun Bae and his{" "}
            <a href="https://github.com/karlla1220/3GPPSchedule" target="_blank" rel="noreferrer" className="underline">
              3GPPSchedule
            </a>{" "}
            project for ideas used here.
          </p>
        </Section>
        <Section title="Credit: Duckhyun Bae's 3GPPSchedule">
          <p>
            <a href="https://github.com/karlla1220/3GPPSchedule" target="_blank" rel="noreferrer" className="underline">
              3GPPSchedule
            </a>{" "}
            by Duckhyun Bae is a separate project that inspired parts of this app. No code was
            copied; the ideas below were rebuilt independently.
          </p>
          <p><strong>Similar</strong></p>
          <ul className="list-disc space-y-1 pl-4">
            <li>Both turn chair schedule files into a readable timetable for several 3GPP groups.</li>
            <li>Both read where each group posts its schedule (RAN4 slides, SA1 agenda, SA2 Session Plan).</li>
            <li>Both connect draft documents to the meeting's agenda items.</li>
          </ul>
          <p><strong>Different</strong></p>
          <ul className="list-disc space-y-1 pl-4">
            <li>This app adds room check-in, "colleague needed" alerts, phone notifications and My agenda.</li>
            <li>This app merges several chair files per meeting and keeps track of which file said what.</li>
            <li>This app never guesses times: unclear blocks stay whole instead of being split.</li>
          </ul>
          <p><strong>Ideas taken from it</strong></p>
          <ul className="list-disc space-y-1 pl-4">
            <li>Only download a file again when it has changed, and list each folder once per update.</li>
            <li>Pick the newest schedule by its own revision, and never replace it with an older one.</li>
            <li>Spot breaks from cell colours and keep unplaced text as notes.</li>
          </ul>
        </Section>
        <Section title="Choose RAN Plenary, RAN1, RAN2, RAN3, RAN4, SA1 or SA2">
          <p>
            Use the <strong>working group dropdown</strong> (e.g. "RAN1 ▾") at the top of any page.
            The whole app
            follows your choice, and your device remembers it.
          </p>
          <ul className="list-disc space-y-1 pl-4">
            <li>
              Now, Schedule, My agenda, Drafts, Rooms, Changes, Meetings and Company all change to
              the selected working group.
            </li>
            <li>
              Each group keeps its own meetings, rooms, agenda items, drafts, check-ins and
              colleague alerts; switching groups does not combine them.
            </li>
            <li>
              <strong>RAN Plenary</strong> reads the chair's "RAN#&lt;n&gt; time plan" in{" "}
              <code>RAN/Inbox/Chair</code>: Main and Breakout lanes, breaks, and meetings held
              during breaks; agenda numbers only where the plan writes "AI x".{" "}
              <strong>RAN1</strong> uses its main online/offline schedule plus chair detail files.{" "}
              <strong>RAN2</strong> uses the single schedule document in its Agenda folder.{" "}
              <strong>RAN3</strong> takes the main session from the weekday table at the end of
              the newest chair notes (<code>Inbox/Chairs_Notes</code>) and the offline rooms from
              the <code>Offline_meeting_room</code> spreadsheet (one sheet per day).{" "}
              <strong>RAN4</strong> reads the newest <code>RAN4_&lt;n&gt;_meeting_schedule_vNN</code>{" "}
              slides in <code>Inbox/Meeting_Arrangements</code>: one slide per day, rooms across
              (Main, the two breakouts, Ad hoc room). Times written inside a cell ("—12:00—",
              "(14:30–15:30)") split it, and "Coffee break AH" items appear during that break. Topic
              numbers such as <code>[201]</code> are turned into agenda items using the chair's{" "}
              <code>List_Topics_moderators</code> workbook, so starring 7.4.2 shows topic [201]; its
              <code>[121][201] …</code> Drafts folder follows too. A Friday "14:00–EOM" block is
              shown until 18:00 and says "(until end of meeting)".{" "}
              <strong>SA2</strong> reads the convenors' newest{" "}
              <code>SA2-&lt;n&gt;-Session Plan - rNN</code> in{" "}
              <code>Inbox/Drafts/_Session_Plan_Updates</code>: Stream 1 in the Main room, Streams 2
              and 3 in the breakouts (or wherever a cell says "In breakout 1"/"In main room"). Each
              quarter (Q1–Q5) is one block listing everything both day columns name — it is never
              split at a guessed half-time. Agenda numbers come only from what is written, e.g.{" "}
              <code>(20.6.18)</code> or <code>(20.6.12 – 16)</code>; "[9]" is a tdoc count. SA2
              Drafts folders are named by work item, so they may not link to an agenda item.{" "}
              <strong>SA1</strong> reads the chair's Q0–Q5 week grid in <code>SA1/Inbox/agenda</code>{" "}
              (the "Breakout sessions schedule" or the weekday table in "Agenda for SA1#&lt;n&gt;",
              whichever was saved last): Plenary / Breakout 1 and Breakout 2 lanes, a line such as
              "(19:15-20:30)" gets its own block, and agenda numbers come from lines like "7.4.3 AI".
            </li>
            <li>
              Drafts come from each group's own inbox. RAN2, RAN3, RAN4, SA1 and SA2 use <code>Inbox/Drafts</code>{" "}
              with a capital D.
            </li>
            <li>
              <strong>RAN3 comebacks:</strong> the pink <code>CB: # 2_Name</code> lines under each
              agenda item in the chair notes. Each has its own Drafts folder (
              <code>CB # 2_Name</code>), so starring the agenda item also shows that folder's drafts.
              When the chair removes "CB:" the comeback shows as <em>closed</em> under My agenda; its
              drafts stay visible.
            </li>
          </ul>
        </Section>

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
              The RAN1 and RAN2 email reflectors are members-only behind an ETSI login, so deadlines
              cannot be read automatically — they are manual and stay on your own device.
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
              meeting Wi-Fi — tried over HTTPS first, then plain HTTP), <strong>Sync</strong> (3GPP
              SYNC mirror) or <strong>Published</strong> (last built snapshot). Duplicates across
              servers are merged.
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
          <ul className="list-disc space-y-1 pl-4">
            <li>
              <strong>Call a colleague:</strong> tap a colleague's name to alert the whole company
              that they're needed in your room. A banner appears on everyone's screen for 10
              minutes — one line per person needed — and anyone can close it for themselves. The
              sender can withdraw it early.
            </li>
            <li>
              <strong>Notifications:</strong> get a system alert even when the app is closed — each
              device opts in separately from the Company page.
              <ul className="mt-1 list-circle space-y-1 pl-4">
                <li>
                  <strong>iPhone:</strong> in Safari tap Share → Add to Home Screen, open 3GPP Companion
                  from your home screen, then Company → Notifications → Enable. (Deleted the app
                  before? Just add it again — nothing auto-prompts.)
                </li>
                <li>
                  <strong>Android:</strong> Company → Notifications → Enable works right away in
                  Chrome. Optional: install via ⋮ → "Add to Home screen" / "Install app".
                </li>
                <li>
                  <strong>Laptop:</strong> Company → Notifications → Enable, and allow the browser's
                  permission prompt.
                </li>
              </ul>
            </li>
          </ul>
          <Link to="/company" className="inline-block underline underline-offset-2">
            Open Company
          </Link>
        </Section>

        <Section title="What this app stores">
          <p>
            3GPP Companion has no accounts, no passwords and no tracking. Here is everything it
            stores, in plain terms:
          </p>
          <ul className="list-disc space-y-1 pl-4">
            <li>
              <strong>On your own device:</strong> your bookmarks, followed agenda items, read
              state, deadlines, display name and check-in live in your browser storage. Clearing
              site data resets them.
            </li>
            <li>
              <strong>Your name and room check-ins</strong> are stored on the server so colleagues
              can see who is where. A check-in expires automatically after two hours without
              activity and is scoped to one meeting. Your location is never used.
            </li>
            <li>
              <strong>Your company code is never stored as text.</strong> Only a one-way scrambled
              (hashed) version is kept, so even someone reading the database cannot tell which
              company codes are in use.
            </li>
            <li>
              <strong>Notification registrations</strong> are per device: a unique push address
              your browser creates, plus two encryption keys used to deliver the alert. No device
              model, browser, operating system or location is stored — and you can turn it off per
              device at any time from the Company page.
            </li>
            <li>
              <strong>"Colleague needed" alerts</strong> are stored for 10 minutes, then deleted.
            </li>
            <li>
              <strong>Nothing else:</strong> no analytics on individuals, no advertising, no data
              shared with anyone outside your company group.
            </li>
          </ul>
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
            Switch meetings within the working group selected at the top. RAN Plenary, RAN1–RAN4, SA1 and SA2 meetings are
            discovered from the official 3GPP portal, so past meetings stay browsable and the next
            one appears automatically — the current meeting is selected for you.
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
            <strong>Where documents come from:</strong> before the meeting (including the day
            before), only the meeting's own 3GPP folder. On the meeting days, only Meetings Sync
            (and the venue server when you are on the meeting Wi-Fi). The day after, the meeting
            folder and Meetings Sync together. The newest version of each file wins.
          </li>
          <li>
            <strong>Timetable checks:</strong> an update is refused, and the previous timetable
            kept, if a document fills time the timetable leaves empty, one table cell lands in two
            rooms, or the same agenda item shows in two rooms at once without a document saying so.
          </li>
          <li>
            <strong>RAN1 venue server:</strong> during the meeting week the app tries to read drafts
            (and, if you switch it on in Schedule → sources, the schedule)
            directly from the meeting-local server at 10.10.10.10 — over HTTPS first, then plain
            HTTP. The HTTPS read only succeeds if that server's security certificate is officially
            issued for the address 10.10.10.10; with a self-signed certificate the browser refuses
            it silently and the app simply falls back to the 3GPP sync mirror. Nothing breaks
            either way.
          </li>
          <li>
            <strong>Remote meeting FTP:</strong> during the meeting week the automatic refresh
            also reads the meeting's remote FTP server (e.g. RAN-Maastricht.3gpp.org), which works
            from outside the venue wifi — handy at night from your hotel. The login is saved once
            by the app owner and is the same at every meeting; only the address changes each
            meeting, and it is entered here: the Drafts page asks for it once, and the first person
            to enter it sets it for everyone. The stored address stays visible on the Drafts page,
            and Change replaces it if the first entry was wrong. You can skip the question.
          </li>
          <li>
            <strong>Meeting week follows the live server:</strong> while the meeting is running,
            the drafts list tracks what the meeting server actually holds. A file it no longer
            lists — an evaluation round the room has moved past, for example — is hidden rather
            than deleted: nothing is removed from the meeting's own archive folder.
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
