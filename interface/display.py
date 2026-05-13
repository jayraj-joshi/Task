"""Pretty-print outline trees (ASCII) and load outline JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List


def load_outline_bundle(path: Path) -> dict[str, Any]:
    """Load a JSON file produced by ``build_outline_from_pdf`` (expects ``structure`` list)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Outline JSON must be an object")
    return data


def count_nodes(nodes: Any) -> int:
    """Total outline nodes (nested)."""
    n = 0
    if isinstance(nodes, dict):
        n = 1
        for c in nodes.get("nodes") or []:
            n += count_nodes(c)
    elif isinstance(nodes, list):
        for item in nodes:
            n += count_nodes(item)
    return n


def max_depth(nodes: Any, d: int = 0) -> int:
    if isinstance(nodes, dict):
        ch = nodes.get("nodes") or []
        if not ch:
            return d + 1
        return max(max_depth(c, d + 1) for c in ch)
    if isinstance(nodes, list):
        if not nodes:
            return d
        return max(max_depth(x, d) for x in nodes)
    return d


def _node_headline(
    node: dict[str, Any],
    *,
    show_pages: bool,
    show_anchor: bool,
    show_chunk: bool,
    anchor_max: int,
) -> str:
    parts: List[str] = []
    nid = node.get("node_id")
    if nid:
        parts.append(f"[{nid}]")
    parts.append(str(node.get("title") or "(untitled)"))
    if show_pages and node.get("start_index") is not None:
        end = node.get("end_index")
        parts.append(f"p{node['start_index']}-{end}")
    if show_chunk and node.get("chunk_excerpt_index") is not None:
        parts.append(f"excerpt#{node['chunk_excerpt_index']}")
    if show_anchor:
        a = str(node.get("split_document_anchor") or "").strip()
        if a:
            one = a.replace("\n", " ").strip()
            if len(one) > anchor_max:
                one = one[: anchor_max - 1] + "…"
            parts.append(f"«{one}»")
    return " ".join(parts)


def _print_summary_lines(summary: str, prefix: str, width: int) -> None:
    s = summary.strip().replace("\n", " ")
    if len(s) <= width:
        print(f"{prefix}{s}")
        return
    line = prefix
    for word in s.split():
        if len(line) + 1 + len(word) > width and len(line) > len(prefix):
            print(line.rstrip())
            line = prefix + word
        else:
            line = (line + " " + word).strip() if line != prefix else prefix + word
    if line.strip():
        print(line.rstrip())


def print_structure_tree(
    nodes: List[dict[str, Any]],
    *,
    prefix: str = "",
    show_summary: bool = False,
    show_pages: bool = True,
    show_anchor: bool = False,
    show_chunk: bool = False,
    summary_width: int = 96,
    anchor_max: int = 72,
) -> None:
    """Print nested ``structure`` nodes as an ASCII tree."""
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        is_last = i == len(nodes) - 1
        branch = "└── " if is_last else "├── "
        head = _node_headline(
            node,
            show_pages=show_pages,
            show_anchor=show_anchor,
            show_chunk=show_chunk,
            anchor_max=anchor_max,
        )
        print(f"{prefix}{branch}{head}")
        if show_summary and node.get("summary"):
            cont = "    " if is_last else "│   "
            _print_summary_lines(str(node["summary"]), prefix + cont + "↳ ", summary_width)
        children = node.get("nodes")
        if isinstance(children, list) and children:
            next_prefix = prefix + ("    " if is_last else "│   ")
            print_structure_tree(
                children,
                prefix=next_prefix,
                show_summary=show_summary,
                show_pages=show_pages,
                show_anchor=show_anchor,
                show_chunk=show_chunk,
                summary_width=summary_width,
                anchor_max=anchor_max,
            )


def print_outline_overview(data: dict[str, Any], *, title: str = "Outline") -> None:
    """Print doc name, optional description, and tree stats."""
    print(f"{title}: {data.get('doc_name', '(unknown)')}")
    if data.get("doc_description"):
        print(f"Description: {str(data['doc_description']).strip()}")
    roots = data.get("structure")
    if isinstance(roots, list):
        print(
            f"Root sections: {len(roots)}  |  Total nodes: {count_nodes(roots)}  |  Max depth: {max_depth(roots)}"
        )
