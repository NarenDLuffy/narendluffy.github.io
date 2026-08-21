import { createFileRoute } from "@tanstack/react-router";
import { Building2, ShieldCheck, Users } from "lucide-react";

export const Route = createFileRoute("/company")({
  head: () => ({
    meta: [
      { title: "My company — RAN1 Live" },
      {
        name: "description",
        content:
          "Coordinate RAN1 session coverage with verified colleagues from your own company. Voluntary room check-in, never GPS.",
      },
      { property: "og:title", content: "My company — RAN1 Live" },
      {
        property: "og:description",
        content:
          "See which rooms colleagues from your verified company are covering during RAN1 week.",
      },
    ],
  }),
  component: CompanyPage,
});

function CompanyPage() {
  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <h1 className="text-lg font-semibold">My company</h1>
        <p className="text-sm text-muted-foreground">
          Coming in the next phase, once verified corporate sign-in is connected.
        </p>
      </header>

      <div className="space-y-2">
        {[
          {
            icon: Users,
            title: "Colleagues by room",
            body: "See which rooms colleagues from your company are covering right now, grouped by room and searchable by person.",
          },
          {
            icon: Building2,
            title: "Session coverage",
            body: "For each parallel session: how many colleagues follow the agenda item and how many are actually in the room. Zero-coverage sessions are flagged.",
          },
          {
            icon: ShieldCheck,
            title: "Company presence & privacy",
            body: "Presence is voluntary and expires automatically. You choose the room — no GPS, no movement history, and nothing is visible outside your verified company.",
          },
        ].map((f) => (
          <section key={f.title} className="flex gap-3 rounded-lg border border-border bg-card p-3">
            <f.icon className="mt-0.5 size-5 shrink-0 text-primary" />
            <div>
              <h2 className="text-sm font-semibold">{f.title}</h2>
              <p className="text-xs text-muted-foreground">{f.body}</p>
            </div>
          </section>
        ))}
      </div>

      <p className="rounded-lg border border-dashed border-border p-3 text-xs text-muted-foreground">
        Access requires a verified corporate email domain. Typing a company name will never grant
        access to that company's presence data, and cross-company isolation is enforced in the
        database, not in the browser.
      </p>
    </div>
  );
}
