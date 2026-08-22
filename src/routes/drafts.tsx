import { createFileRoute, Link, Outlet, useRouterState } from "@tanstack/react-router";

export const Route = createFileRoute("/drafts")({
  head: () => ({
    meta: [
      { title: "Draft activity — RAN1 Live" },
      {
        name: "description",
        content:
          "Live view of RAN1 drafts and feature lead summaries as they are uploaded, mapped to the agenda items you follow.",
      },
      { property: "og:title", content: "Draft activity — RAN1 Live" },
      {
        property: "og:description",
        content: "RAN1 drafts and FL summaries, tracked per agenda item as they appear.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: DraftsLayout,
});

function DraftsLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (
    <div>
      {pathname !== "/drafts" ? (
        <Link
          to="/drafts"
          className="mb-3 inline-block text-xs font-medium text-muted-foreground underline underline-offset-2"
        >
          ← All draft activity
        </Link>
      ) : null}
      <Outlet />
    </div>
  );
}
