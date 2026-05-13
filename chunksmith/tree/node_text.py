"""Fill outline node ``text`` from PDF pages using ``start_index`` / ``end_index``."""

from __future__ import annotations

from typing import Any, List


def _needle_in_blob(node: dict[str, Any], blob: str) -> str:
    """Prefer ``split_document_anchor``, then ``title``, first substring that appears in ``blob``."""
    for key in ("split_document_anchor", "title"):
        v = str(node.get(key) or "").strip()
        if v and v in blob:
            return v
    return ""


def page_span_plain_text(
    start_1b: int,
    end_1b_inclusive: int,
    pdf_pages: List[tuple[str, int]],
) -> str:
    """Concatenate extracted text for PDF pages ``start_1b`` … ``end_1b_inclusive`` (1-based, inclusive)."""
    s = int(start_1b)
    e = int(end_1b_inclusive)
    if e < s:
        s, e = e, s
    parts: List[str] = []
    for pi in range(s - 1, e):
        if 0 <= pi < len(pdf_pages):
            parts.append(pdf_pages[pi][0])
    return "".join(parts)


def iter_outline_nodes_preorder(tree: Any) -> List[dict[str, Any]]:
    """Depth-first pre-order over nested ``nodes`` (same order as typical reading / JSON walk)."""
    out: List[dict[str, Any]] = []

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            out.append(x)
            ch = x.get("nodes")
            if isinstance(ch, list):
                for c in ch:
                    walk(c)
        elif isinstance(x, list):
            for item in x:
                walk(item)

    walk(tree)
    return out


def add_node_text(tree: Any, pdf_pages: List[tuple[str, int]]) -> None:
    """
    Set each node's ``text`` to the slice of its page span that belongs to that section.

    Builds plain text from ``start_index`` … ``end_index`` (inclusive), then cuts from this node's
    heading needle to the next outline node's needle in pre-order (so siblings on the same page do
    not duplicate each other's bodies). If no needle matches, uses the full page span.
    """
    nodes = iter_outline_nodes_preorder(tree)
    for i, node in enumerate(nodes):
        start_p = node.get("start_index")
        end_p = node.get("end_index")
        if start_p is None or end_p is None:
            continue
        blob = page_span_plain_text(int(start_p), int(end_p), pdf_pages).strip()
        if not blob:
            node["text"] = ""
            continue
        start_needle = _needle_in_blob(node, blob)
        next_needle = ""
        if i + 1 < len(nodes):
            next_needle = _needle_in_blob(nodes[i + 1], blob)
        if start_needle:
            start_char = blob.find(start_needle)
            end_char = len(blob)
            if next_needle:
                nx = blob.find(next_needle, start_char + max(1, len(start_needle)))
                if nx >= 0:
                    end_char = nx
            node["text"] = blob[start_char:end_char].strip()
        else:
            node["text"] = blob
