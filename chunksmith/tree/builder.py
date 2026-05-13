"""Merge flat TOC rows, convert indices, build nested tree, assign node IDs."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, List, Optional, Union

from chunksmith.config import RuntimeSettings, load_settings
from chunksmith.exceptions import OutlineExtractionError
from chunksmith.llm_support import doc_description, extractor
from chunksmith.parser import chunker, document
from chunksmith.tree import schema
from chunksmith.tree.node_text import add_node_text


def convert_physical_index_to_int(data: List[dict[str, Any]]) -> None:
    """Normalize ``physical_index`` strings like ``<physical_index_5>`` to ints in-place."""
    for item in data:
        if not isinstance(item, dict) or "physical_index" not in item:
            continue
        pi = item["physical_index"]
        if isinstance(pi, str):
            if pi.startswith("<physical_index_"):
                item["physical_index"] = int(pi.split("_")[-1].rstrip(">").strip())
            elif pi.startswith("physical_index_"):
                item["physical_index"] = int(pi.split("_")[-1].strip())
            else:
                try:
                    item["physical_index"] = int(pi.strip())
                except ValueError:
                    # If it's not a number, we might have to leave it or handle it elsewhere
                    pass


def _physical_page_at_char(tagged_excerpt: str, char_index: int) -> int:
    """
    Map a character offset in tagged excerpt text to the 1-based PDF page for that position.

    Excerpts contain repeated ``<physical_index_N>`` markers; the active page updates at each marker
    encountered before ``char_index``.
    """
    i = 0
    current = 1
    limit = max(0, min(len(tagged_excerpt), char_index))
    prefix = "<physical_index_"
    plen = len(prefix)
    while i < limit:
        if tagged_excerpt.startswith(prefix, i):
            j = tagged_excerpt.find(">", i)
            if j == -1:
                break
            current = int(tagged_excerpt[i + plen : j])
            i = j + 1
        else:
            i += 1
    return current


def _find_row_start_in_excerpt(excerpt: str, row: dict[str, Any], search_from: int) -> int:
    """First index of anchor text or title in ``excerpt`` at/after ``search_from``, or -1."""
    anchor = str(row.get("split_document_anchor") or "").strip()
    if anchor:
        p = excerpt.find(anchor, search_from)
        if p >= 0:
            return p
    title = str(row.get("title") or "").strip()
    if title:
        p = excerpt.find(title, search_from)
        if p >= 0:
            return p
    return -1


def refine_physical_index_from_excerpt_tags(
    rows: List[dict[str, Any]],
    chunk_idx_per_row: List[int],
    groups: List[str],
) -> None:
    """
    Correct each row's ``physical_index`` using ``<physical_index_N>`` tags in the LLM excerpt.

    The model often confuses section numbers in titles (e.g. ``3 Model Architecture``) with PDF page 3;
    mapping the anchor/title offset to the tagged excerpt fixes page spans (e.g. Background end page).
    """
    if not rows or len(chunk_idx_per_row) != len(rows):
        return
    prev_chunk = -1
    scan_from = 0
    for row, chi in zip(rows, chunk_idx_per_row):
        if not isinstance(row, dict) or row.get("physical_index") is None:
            continue
        if not isinstance(chi, int) or chi < 0 or chi >= len(groups):
            continue
        excerpt = groups[chi]
        if chi != prev_chunk:
            scan_from = 0
            prev_chunk = chi
        pos = _find_row_start_in_excerpt(excerpt, row, scan_from)
        if pos < 0:
            continue
        try:
            row["physical_index"] = _physical_page_at_char(excerpt, pos)
        except ValueError:
            continue
        scan_from = pos + 1


def refine_physical_index_from_pdf_page_text(
    rows: List[dict[str, Any]],
    page_list: List[tuple[str, int]],
) -> None:
    """
    Snap each row's ``physical_index`` to the PDF page whose extracted text contains the heading.

    Runs after excerpt-tag refinement. Fixes cases where the model maps a section *number* (e.g. ``3``)
    to a PDF page, or substring search in tagged chunks misses (spacing/extraction quirks). Uses the same
    ``page_list`` as ``<physical_index_N>`` tagging, so parent sections (e.g. ``3 Model Architecture``)
    get ``start_index`` 2 and ``end_index`` 3 when the heading is on page 2 and the next subsection starts
    on page 3.
    """
    if not rows or not page_list:
        return
    texts = [p[0] for p in page_list]
    n = len(texts)
    # Scan forward from the previous section's page so same-page headings are found, without matching
    # an earlier duplicate needle on a prior page when possible.
    prev_page = 1
    for row in rows:
        if not isinstance(row, dict) or row.get("physical_index") is None:
            continue
        anchor = str(row.get("split_document_anchor") or "").strip()
        title = str(row.get("title") or "").strip()
        needles: List[str] = []
        if anchor:
            needles.append(anchor)
        if title and title not in needles:
            needles.append(title)
        if not needles:
            continue
        found: int | None = None
        lo = max(0, prev_page - 1)
        for pi in range(lo, n):
            body = texts[pi]
            for needle in needles:
                if needle in body:
                    found = pi + 1
                    break
            if found is not None:
                break
        if found is not None:
            row["physical_index"] = found
            prev_page = found


def add_preface_if_needed(
    data: List[dict[str, Any]], *, include_summary: bool = False
) -> List[dict[str, Any]]:
    if not data:
        return data
    if data[0].get("physical_index") is not None and data[0]["physical_index"] > 1:
        row: dict[str, Any] = {"structure": "0", "title": "Preface", "physical_index": 1}
        if include_summary:
            row["summary"] = ""
        data.insert(0, row)
    return data


def list_to_tree(data: List[dict[str, Any]]) -> List[dict[str, Any]]:
    def get_parent_structure(structure: str | None) -> str | None:
        if not structure:
            return None
        parts = str(structure).split(".")
        return ".".join(parts[:-1]) if len(parts) > 1 else None

    nodes: dict[str, dict[str, Any]] = {}
    root_nodes: List[dict[str, Any]] = []

    for item in data:
        structure = item.get("structure")
        sk = str(structure) if structure is not None else ""
        node = {
            "title": item.get("title"),
            "start_index": item.get("start_index"),
            "end_index": item.get("end_index"),
            "nodes": [],
        }
        if "summary" in item:
            node["summary"] = str(item.get("summary") or "").strip()
        anchor = str(item.get("split_document_anchor") or "").strip()
        if anchor:
            node["split_document_anchor"] = anchor
        cxi = item.get("chunk_excerpt_index")
        if cxi is not None:
            node["chunk_excerpt_index"] = int(cxi)
        nodes[sk] = node
        parent_structure = get_parent_structure(sk if sk else None)

        if parent_structure:
            if parent_structure in nodes:
                nodes[parent_structure]["nodes"].append(node)
            else:
                root_nodes.append(node)
        else:
            root_nodes.append(node)

    def clean_node(node: dict[str, Any]) -> dict[str, Any]:
        if not node.get("nodes"):
            node.pop("nodes", None)
        else:
            for child in node["nodes"]:
                clean_node(child)
        return node

    return [clean_node(n) for n in root_nodes]


def post_processing(structure: List[dict[str, Any]], end_physical_index: int) -> List[dict[str, Any]]:
    for i, item in enumerate(structure):
        item["start_index"] = item.get("physical_index")
        if i < len(structure) - 1:
            if structure[i + 1].get("appear_start") == "yes":
                item["end_index"] = structure[i + 1]["physical_index"] - 1
            else:
                item["end_index"] = structure[i + 1]["physical_index"]
        else:
            item["end_index"] = end_physical_index
    tree = list_to_tree(structure)
    if tree:
        return tree
    for node in structure:
        node.pop("appear_start", None)
        node.pop("physical_index", None)
    return structure


def write_node_id(data: Any, node_id: int = 0) -> int:
    if isinstance(data, dict):
        data["node_id"] = str(node_id).zfill(4)
        node_id += 1
        children = data.get("nodes")
        if isinstance(children, list):
            for item in children:
                node_id = write_node_id(item, node_id)
    elif isinstance(data, list):
        for item in data:
            node_id = write_node_id(item, node_id)
    return node_id


def build_outline_from_pdf(
    pdf_path: Union[str, Path],
    settings: Optional[RuntimeSettings] = None,
    *,
    add_text: bool = False,
    assign_node_ids: bool = False,
    add_summary: bool = False,
    add_word_range: bool = False,
    generate_doc_summary: Optional[bool] = None,
) -> dict[str, Any]:
    """
    End-to-end no-TOC outline: PDF → tagged chunks → LLM flat rows → tree.

    If ``add_word_range`` is True, each row also has ``split_document_anchor`` (verbatim excerpt substring at the
    section start) and ``chunk_excerpt_index`` (which LLM chunk produced that row).
    """
    settings = settings or load_settings()
    path = Path(pdf_path).resolve()
    page_list = document.load_pdf_pages(path, settings)
    if not page_list:
        raise OutlineExtractionError("No pages extracted from PDF")

    tagged, lengths = chunker.build_tagged_page_strings(
        page_list, start_index=1, model=settings.pageindex_model
    )
    groups = chunker.page_list_to_group_text(
        tagged,
        lengths,
        max_tokens=settings.max_tokens_per_chunk,
        overlap_page=settings.overlap_pages,
    )

    init_rows = extractor.generate_toc_init(
        settings,
        groups[0],
        include_summary=add_summary,
        include_word_range=add_word_range,
    )
    chunk_of_row: List[int] = [0] * len(init_rows)
    flat = list(init_rows)
    for chunk_idx, part in enumerate(groups[1:], start=1):
        cont_rows = extractor.generate_toc_continue(
            settings,
            flat,
            part,
            include_summary=add_summary,
            include_word_range=add_word_range,
        )
        chunk_of_row.extend([chunk_idx] * len(cont_rows))
        flat.extend(cont_rows)

    convert_physical_index_to_int(flat)
    before_preface = len(chunk_of_row)
    flat = add_preface_if_needed(flat, include_summary=add_summary)
    if len(flat) == before_preface + 1:
        chunk_of_row.insert(0, 0)
    if add_word_range and flat and str(flat[0].get("title", "")).strip() == "Preface":
        flat[0].setdefault("split_document_anchor", "Preface")

    paired = [(c, x) for c, x in zip(chunk_of_row, flat) if x.get("physical_index") is not None]
    chunk_of_row = [p[0] for p in paired]
    flat = [p[1] for p in paired]

    refine_physical_index_from_excerpt_tags(flat, chunk_of_row, groups)
    refine_physical_index_from_pdf_page_text(flat, page_list)

    try:
        validated = schema.validate_toc_rows(flat)
        use_rows: List[dict[str, Any]] = []
        for i, r in enumerate(validated):
            d = r.model_dump()
            if add_word_range:
                d["chunk_excerpt_index"] = chunk_of_row[i]
            use_rows.append(d)
    except Exception as e:
        raise OutlineExtractionError(f"TOC row validation failed: {e}") from e
    if not add_summary:
        for d in use_rows:
            d.pop("summary", None)
    if not add_word_range:
        for d in use_rows:
            d.pop("split_document_anchor", None)
            d.pop("chunk_excerpt_index", None)

    end_page = len(page_list)
    tree = post_processing(copy.deepcopy(use_rows), end_page)

    if assign_node_ids:
        write_node_id(tree)

    if add_text:
        add_node_text(tree, page_list)

    do_doc_summary = (
        settings.generate_doc_summary if generate_doc_summary is None else generate_doc_summary
    )
    out: dict[str, Any] = {
        "doc_name": path.name,
        "structure": tree,
    }
    if do_doc_summary:
        out["doc_description"] = doc_description.generate_doc_description(
            settings, tree, model=settings.pageindex_model
        )
    return out
