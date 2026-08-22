import { useState } from "react";
import { ChevronDown, ChevronRight, ExternalLink, Folder, FolderOpen } from "lucide-react";
import { ArtifactRow } from "@/components/DraftActivity";
import { cn } from "@/lib/utils";
import type { DraftTreeNode } from "@/services/draftService";
import type { DraftArtifact, DraftFolder } from "@/types/drafts";

/**
 * Generic renderer for whatever folder structure the scanner discovered.
 *
 * There is deliberately no RoundList / RoundCard component: a round is only a
 * label on a generic folder, so a meeting that uses "Further discussion",
 * "Wednesday" or no folders at all renders through exactly this code path.
 */

const TYPE_LABEL: Partial<Record<DraftFolder["folderType"], string>> = {
  round: "Round",
  fl: "FL",
  agenda: "Agenda",
};

function FolderLabel({ folder }: { folder: DraftFolder }) {
  const label = TYPE_LABEL[folder.folderType];
  return label && folder.folderType !== "agenda" ? (
    <span className="mono-code shrink-0 rounded border border-border px-1 py-0.5 text-[10px] uppercase text-muted-foreground">
      {label}
    </span>
  ) : null;
}

/** Breadcrumbs of the *actual* discovered path — never a padded hierarchy. */
export function DraftBreadcrumbs({ trail }: { trail: string[] }) {
  if (trail.length === 0) return null;
  return (
    <p className="flex flex-wrap items-center gap-1 text-[11px] text-muted-foreground">
      {trail.map((part, i) => (
        <span key={`${part}-${i}`} className="flex items-center gap-1">
          {i > 0 ? <span aria-hidden>›</span> : null}
          <span className="truncate">{part}</span>
        </span>
      ))}
    </p>
  );
}

export function DraftFileList({ files }: { files: DraftArtifact[] }) {
  if (files.length === 0) return null;
  return (
    <ol className="space-y-1.5">
      {files.map((file) => (
        <li key={file.id}>
          <ArtifactRow artifact={file} />
        </li>
      ))}
    </ol>
  );
}

export function DraftFolderNode({
  node,
  defaultOpen = true,
}: {
  node: DraftTreeNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const { folder } = node;
  const empty = node.subtreeFileCount === 0;

  return (
    <li className="space-y-1.5">
      <div className="flex items-center gap-2 rounded-md border border-border bg-card p-2.5">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="flex min-w-0 flex-1 items-center gap-2 text-left"
        >
          {open ? (
            <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" />
          )}
          {open ? (
            <FolderOpen className="size-4 shrink-0 text-muted-foreground" />
          ) : (
            <Folder className="size-4 shrink-0 text-muted-foreground" />
          )}
          <span className="min-w-0 flex-1 truncate text-sm font-medium">{folder.name}</span>
          <FolderLabel folder={folder} />
          <span className="mono-code shrink-0 text-[11px] text-muted-foreground">
            {node.subtreeFileCount} file{node.subtreeFileCount === 1 ? "" : "s"}
          </span>
        </button>
        {folder.url ? (
          <a
            href={folder.url}
            target="_blank"
            rel="noreferrer"
            aria-label={`Open ${folder.name} on the source server`}
            className="shrink-0 text-muted-foreground"
          >
            <ExternalLink className="size-3.5" />
          </a>
        ) : null}
      </div>

      {open ? (
        <div className={cn("space-y-1.5", node.breadcrumbs.length > 1 && "border-l border-border pl-3")}>
          <DraftFileList files={node.files} />
          {node.children.length > 0 ? (
            <ul className="space-y-1.5">
              {node.children.map((child) => (
                <DraftFolderNode
                  key={child.folder.id}
                  node={child}
                  // Open a level automatically only when it is small enough to
                  // stay readable; deep or wide trees stay collapsed.
                  defaultOpen={node.children.length <= 3 && child.subtreeFileCount > 0}
                />
              ))}
            </ul>
          ) : null}
          {empty ? (
            <p className="pl-1 text-[11px] text-muted-foreground">Empty so far.</p>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

export function DraftTree({
  nodes,
  looseFiles = [],
}: {
  nodes: DraftTreeNode[];
  /** Files sitting directly in the agenda folder, with no sub-folder at all. */
  looseFiles?: DraftArtifact[];
}) {
  if (nodes.length === 0 && looseFiles.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-border p-3 text-xs text-muted-foreground">
        No draft files uploaded for this agenda item yet.
      </p>
    );
  }
  return (
    <div className="space-y-1.5">
      <DraftFileList files={looseFiles} />
      {nodes.length > 0 ? (
        <ul className="space-y-1.5">
          {nodes.map((node) => (
            <DraftFolderNode key={node.folder.id} node={node} />
          ))}
        </ul>
      ) : null}
    </div>
  );
}
