"""LLM calls for init/continue outline extraction."""

from __future__ import annotations

import json
import logging
from typing import Any, List

from chunksmith.config import RuntimeSettings
from chunksmith.exceptions import OutlineExtractionError
from chunksmith.llm_support import client
from chunksmith.llm_support.prompts import (
    ANCHOR_INSTRUCTION,
    SUMMARY_INSTRUCTION,
    TOC_CONTINUE_SYSTEM,
    TOC_INIT_SYSTEM,
)

logger = logging.getLogger(__name__)


def _outline_extra_instructions(*, include_summary: bool, include_word_range: bool) -> str:
    parts: List[str] = []
    if include_summary:
        parts.append(SUMMARY_INSTRUCTION.strip())
    if include_word_range:
        parts.append(ANCHOR_INSTRUCTION.strip())
    if not parts:
        return ""
    return "\n" + "\n".join(parts)


def format_given_text_block(part: str) -> str:
    """Prefix the document excerpt for the outline prompt (verbatim anchor must match this text)."""
    return f"\nGiven text\n:{part}"


def _rows_from_legacy_response(response: str) -> List[dict[str, Any]]:
    """Parse free-form assistant text: prefer ``{"sections": [...]}``, else bare array."""
    parsed = client.extract_json(response)
    if isinstance(parsed, dict) and "sections" in parsed:
        inner = parsed["sections"]
        if isinstance(inner, list):
            return inner
    if isinstance(parsed, list):
        return parsed
    return []


def generate_toc_init(
    settings: RuntimeSettings,
    part: str,
    model: str | None = None,
    *,
    include_summary: bool = False,
    include_word_range: bool = False,
) -> List[dict[str, Any]]:
    m = model or settings.pageindex_model
    head = TOC_INIT_SYSTEM.strip() + _outline_extra_instructions(
        include_summary=include_summary,
        include_word_range=include_word_range,
    )
    prompt = head + format_given_text_block(part)

    response, finish_reason = client.llm_completion(
        settings, m, prompt, return_finish_reason=True, max_tokens=8192
    )
    if finish_reason != "finished":
        raise OutlineExtractionError(f"generate_toc_init finish_reason={finish_reason!r}")
    rows = _rows_from_legacy_response(response)
    if not rows:
        raise OutlineExtractionError("generate_toc_init: no sections in model output")
    return rows


def generate_toc_continue(
    settings: RuntimeSettings,
    toc_content: List[dict[str, Any]],
    part: str,
    model: str | None = None,
    *,
    include_summary: bool = False,
    include_word_range: bool = False,
) -> List[dict[str, Any]]:
    m = model or settings.pageindex_model
    head = TOC_CONTINUE_SYSTEM.strip() + _outline_extra_instructions(
        include_summary=include_summary,
        include_word_range=include_word_range,
    )
    prompt = (
        head
        + format_given_text_block(part)
        + "\nPrevious outline (JSON)\n:"
        + json.dumps(toc_content, indent=2)
    )

    response, finish_reason = client.llm_completion(
        settings, m, prompt, return_finish_reason=True, max_tokens=8192
    )
    if finish_reason != "finished":
        raise OutlineExtractionError(f"generate_toc_continue finish_reason={finish_reason!r}")
    rows = _rows_from_legacy_response(response)
    if not rows:
        raise OutlineExtractionError("generate_toc_continue: no sections in model output")
    return rows
