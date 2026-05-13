"""CLI: build PDF outlines, visualize JSON trees, show config (lives outside ``src/chunksmith``)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from interface.display import (
    load_outline_bundle,
    print_outline_overview,
    print_structure_tree,
)


from chunksmith.config import load_settings  # noqa: E402


def _cmd_build(ns: argparse.Namespace) -> int:
    from chunksmith import build_outline_from_pdf

    pdf = Path(ns.pdf).resolve()
    if not pdf.is_file():
        print(f"error: not a file: {pdf}", file=sys.stderr)
        return 2
    settings = load_settings()
    result = build_outline_from_pdf(
        pdf,
        settings,
        add_text=not ns.no_text,
        assign_node_ids=ns.node_ids,
        add_summary=ns.summary,
        add_word_range=ns.word_range,
        generate_doc_summary=ns.doc_summary or None,
    )
    if ns.print_tree:
        print(file=sys.stderr)
        print_outline_overview(result, title="Built")
        roots = result.get("structure")
        if isinstance(roots, list):
            print_structure_tree(
                roots,
                show_summary=ns.tree_summary,
                show_pages=True,
                show_anchor=ns.tree_anchor,
                show_chunk=ns.tree_chunk,
            )
        print(file=sys.stderr)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if ns.output:
        ns.output.write_text(text, encoding="utf-8")
        print(f"Wrote {ns.output}", file=sys.stderr)
        
        # Also write TOON file (summaries only)
        from chunksmith import toon
        from typing import Any
        def _strip_text(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: _strip_text(v) for k, v in obj.items() if k != "text"}
            if isinstance(obj, list):
                return [_strip_text(x) for x in obj]
            return obj
        toon_text = toon.encode(_strip_text(result))
        toon_path = ns.output.with_suffix(".toon")
        toon_path.write_text(toon_text, encoding="utf-8")
        print(f"Wrote {toon_path}", file=sys.stderr)
    else:
        print(text)
    return 0


def _cmd_tree(ns: argparse.Namespace) -> int:
    path = Path(ns.json_path).resolve()
    if not path.is_file():
        print(f"error: not a file: {path}", file=sys.stderr)
        return 2
    try:
        data = load_outline_bundle(path)
    except (json.JSONDecodeError, OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print_outline_overview(data, title="File")
    roots = data.get("structure")
    if not isinstance(roots, list):
        print("error: missing 'structure' array", file=sys.stderr)
        return 2
    print()
    print_structure_tree(
        roots,
        show_summary=ns.summary,
        show_pages=not ns.no_pages,
        show_anchor=ns.anchor,
        show_chunk=ns.chunk,
    )
    return 0


def _cmd_info(ns: argparse.Namespace) -> int:
    s = load_settings()
    key = s.openai_api_key or ""
    masked = "(not set)"
    if key:
        masked = f"{key[:4]}…{key[-4:]}" if len(key) > 8 else "(set)"
    print("ChunkSmith PageIndexer — runtime settings")
    print(f"  pageindex_model:     {s.pageindex_model}")
    print(f"  pdf_parser:          {s.pdf_parser}")
    print(f"  max_tokens_per_chunk:{s.max_tokens_per_chunk}")
    print(f"  overlap_pages:       {s.overlap_pages}")
    print(f"  generate_doc_summary:{s.generate_doc_summary}")
    print(f"  openai_api_key:      {masked}")
    if s.azure_openai_endpoint:
        print(f"  azure endpoint:      {s.azure_openai_endpoint}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chunksmith-pageindex",
        description="ChunkSmith PageIndexer — PDF outline (LLM) + nested tree utilities.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="Run outline extraction on a PDF (requires API keys / env).")
    b.add_argument("pdf", type=Path, help="Path to PDF")
    b.add_argument("-o", "--output", type=Path, default=None, help="Write JSON here (default: stdout)")
    b.add_argument("--no-text", "--notext", action="store_true", dest="no_text", help="Omit per-node text")
    b.add_argument("--summary", action="store_true", help="Per-section summaries from the outline LLM")
    b.add_argument(
        "--word-range",
        action="store_true",
        dest="word_range",
        help="Request split_document_anchor (+ chunk_excerpt_index)",
    )
    b.add_argument(
        "--node-ids",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Assign node_id (default: true)",
    )
    b.add_argument("--doc-summary", action="store_true", dest="doc_summary", help="Separate doc_description LLM call")
    b.add_argument(
        "--print-tree",
        action="store_true",
        help="After build, print ASCII tree to stderr (JSON still goes to -o or stdout)",
    )
    b.add_argument("--tree-summary", action="store_true", help="With --print-tree, show summaries under nodes")
    b.add_argument("--tree-anchor", action="store_true", help="With --print-tree, show split_document_anchor")
    b.add_argument("--tree-chunk", action="store_true", help="With --print-tree, show chunk_excerpt_index")
    b.set_defaults(func=_cmd_build)

    t = sub.add_parser("tree", help="Print an ASCII tree from an outline JSON file (no LLM).")
    t.add_argument("json_path", type=Path, help="Path to outline JSON")
    t.add_argument("--summary", action="store_true", help="Show per-node summary lines")
    t.add_argument("--anchor", action="store_true", help="Show split_document_anchor snippets")
    t.add_argument("--chunk", action="store_true", help="Show chunk_excerpt_index")
    t.add_argument("--no-pages", action="store_true", help="Hide p{start}-{end} on each line")
    t.set_defaults(func=_cmd_tree)

    i = sub.add_parser("info", help="Show resolved settings (API key masked).")
    i.set_defaults(func=_cmd_info)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    return int(ns.func(ns))


if __name__ == "__main__":
    raise SystemExit(main())
