"""Pydantic models for LLM flat rows and optional nested outline nodes."""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, TypeAdapter


class TocFlatRow(BaseModel):
    """One outline row (LLM output)."""

    model_config = ConfigDict(extra="ignore")

    structure: str
    title: str = ""
    physical_index: str | int | None = None
    # Filled when ``add_summary=True`` on ``build_outline_from_pdf`` (same outline API calls).
    summary: str = ""
    # When ``add_word_range=True``: verbatim substring from the excerpt at the section start.
    split_document_anchor: str = Field(
        default="",
        validation_alias=AliasChoices(
            "split_document_anchor",
            "document_anchor_word",
            "split_from_document_word",
        ),
    )


def validate_toc_rows(raw: Any) -> List[TocFlatRow]:
    if not isinstance(raw, list):
        return []
    adapter = TypeAdapter(List[TocFlatRow])
    return adapter.validate_python(raw)


class OutlineNode(BaseModel):
    """Nested node after ``post_processing`` / ``list_to_tree`` (optional validation)."""

    model_config = ConfigDict(extra="allow")

    title: str = ""
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    node_id: Optional[str] = None
    summary: Optional[str] = None
    split_document_anchor: Optional[str] = None
    text: Optional[str] = None
    nodes: Optional[List[OutlineNode]] = None
