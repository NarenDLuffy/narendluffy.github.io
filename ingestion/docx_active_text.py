"""Extract the active visible text from WordprocessingML elements.

Schedule revisions are often represented as direct formatting rather than
tracked changes. Highlighted or inserted text remains active; deleted, hidden,
struck-through, and double-struck text does not.
"""

from __future__ import annotations

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _inside(element, tag: str) -> bool:
    parent = element.getparent()
    while parent is not None:
        if parent.tag == f"{W}{tag}":
            return True
        parent = parent.getparent()
    return False


def _run_is_inactive(run) -> bool:
    properties = run.find(f"{W}rPr")
    return properties is not None and any(
        properties.find(f"{W}{tag}") is not None
        for tag in ("strike", "dstrike", "vanish", "webHidden")
    )


def active_run_text(run) -> str:
    """Text from one active run, including tabs and line breaks."""
    if _run_is_inactive(run) or _inside(run, "del") or _inside(run, "moveFrom"):
        return ""
    pieces: list[str] = []
    for child in run.iterchildren():
        if child.tag == f"{W}t" and child.text:
            pieces.append(child.text)
        elif child.tag == f"{W}tab":
            pieces.append("\t")
        elif child.tag in (f"{W}br", f"{W}cr"):
            pieces.append("\n")
    return "".join(pieces)


def active_paragraph_text(paragraph) -> str:
    """Visible active text from a paragraph, including tracked insertions."""
    return "".join(active_run_text(run) for run in paragraph.iter(f"{W}r"))


def active_element_text(element, separator: str = "\n") -> str:
    """Visible active text from every paragraph below an XML element."""
    paragraphs = [active_paragraph_text(p).strip() for p in element.iter(f"{W}p")]
    return separator.join(text for text in paragraphs if text)