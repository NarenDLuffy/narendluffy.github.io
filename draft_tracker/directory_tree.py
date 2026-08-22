"""Stage 1-4 of the draft pipeline: discover the raw tree, interpret nothing.

The server directory tree is the source of truth. This module crawls every
descendant of the drafts root and returns a normalized in-memory tree. It has
no notion of agenda items, rounds, FL folders or any RAN1 convention - those
semantics are applied later, by the tracker, on top of the finished tree.

Depth is bounded only by a runaway guard, never by an expected layout.
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterable

# Guards against a pathological/looping listing, not against real structures.
SAFETY_MAX_DEPTH = 32
SAFETY_MAX_NODES = 6000


def normalize_path(parts: Iterable[str]) -> str:
    cleaned = [re.sub(r"\s+", " ", p).strip().lower() for p in parts if p]
    return "/".join(cleaned)


@dataclass
class TreeNode:
    """One folder or file as discovered, before any interpretation."""

    name: str
    url: str
    is_dir: bool
    parts: list[str]
    depth: int
    parent: "TreeNode | None" = None
    size: int | None = None
    modified_at: str | None = None
    children: list["TreeNode"] = field(default_factory=list)

    @property
    def normalized_path(self) -> str:
        return normalize_path(self.parts)

    @property
    def parent_path(self) -> str | None:
        return self.parent.normalized_path if self.parent else None

    def walk(self) -> Iterable["TreeNode"]:
        yield self
        for child in self.children:
            yield from child.walk()

    def ancestors(self) -> Iterable["TreeNode"]:
        node = self.parent
        while node is not None:
            yield node
            node = node.parent


def build_tree(
    source: Any,
    root_url: str,
    *,
    max_depth: int = SAFETY_MAX_DEPTH,
    max_nodes: int = SAFETY_MAX_NODES,
) -> TreeNode:
    """Breadth-first crawl of the whole subtree under `root_url`.

    Breadth-first on purpose: when a guard trims a huge tree, the shallow
    (agenda-level) structure is complete rather than one deep branch.
    """
    root = TreeNode(name="drafts", url=root_url, is_dir=True, parts=[], depth=0)
    queue: deque[TreeNode] = deque([root])
    visited_urls: set[str] = {root_url}
    nodes = 0

    while queue:
        folder = queue.popleft()
        if folder.depth >= max_depth or nodes >= max_nodes:
            continue
        for entry in source.list_directory(folder.url):
            nodes += 1
            if nodes > max_nodes:
                break
            child = TreeNode(
                name=entry.name,
                url=entry.url,
                is_dir=entry.is_dir,
                parts=[*folder.parts, entry.name],
                depth=folder.depth + 1,
                parent=folder,
                size=entry.size,
                modified_at=entry.modified_at,
            )
            folder.children.append(child)
            if child.is_dir and child.url not in visited_urls:
                visited_urls.add(child.url)
                queue.append(child)

    return root
