"""One-shot document description after the outline tree is built (separate LLM call from TOC extraction)."""

from __future__ import annotations

import json
import logging
from typing import Any

from chunksmith.config import RuntimeSettings
from chunksmith.llm_support import prompts
from chunksmith.llm_support.client import llm_completion

logger = logging.getLogger(__name__)


def create_clean_structure_for_description(structure: Any) -> Any:
    """
    Strip heavy fields (e.g. full ``text``) before sending the tree to the description model.
    Keeps ``title``, ``node_id``, ``summary``, and nested ``nodes``.
    """
    if isinstance(structure, dict):
        clean_node: dict[str, Any] = {}
        for key in ("title", "node_id", "summary"):
            if key in structure:
                clean_node[key] = structure[key]
        children = structure.get("nodes")
        if isinstance(children, list) and children:
            clean_node["nodes"] = create_clean_structure_for_description(children)
        return clean_node
    if isinstance(structure, list):
        return [create_clean_structure_for_description(item) for item in structure]
    return structure


def generate_doc_description(
    settings: RuntimeSettings,
    structure: Any,
    *,
    model: str | None = None,
) -> str:
    """
    Second-phase LLM: one plain completion, no chat history, unrelated to TOC init/continue prompts.
    """
    clean = create_clean_structure_for_description(structure)
    structure_json = json.dumps(clean, ensure_ascii=False, indent=2)
    prompt = prompts.build_doc_description_prompt(structure_json)
    raw = llm_completion(settings, model, prompt, chat_history=None, max_tokens=2048)
    text = (raw or "").strip()
    if not text or text == "Error":
        logger.warning("Document description LLM returned empty or error placeholder")
    return text
