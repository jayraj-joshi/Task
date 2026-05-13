"""Runtime settings: env vars + optional YAML defaults (no secrets in YAML)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

_DEFAULTS_PATH = Path(__file__).resolve().parent / "config.defaults.yaml"


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None or v == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class RuntimeSettings:
    """Resolved settings for one process."""

    openai_api_key: str | None
    pageindex_model: str
    pdf_parser: str
    max_tokens_per_chunk: int
    overlap_pages: int
    #: After the full tree is built, run an extra LLM call for ``doc_description`` (separate from TOC prompts).
    generate_doc_summary: bool
    azure_openai_endpoint: str | None
    azure_openai_api_key: str | None
    azure_openai_api_version: str | None
    azure_openai_chat_model: str | None
    hf_token: str | None
    rag_model: str


def _load_yaml_defaults(path: Path | None = None) -> dict[str, Any]:
    p = path or _DEFAULTS_PATH
    if not p.is_file():
        return {}
    with p.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_settings(*, defaults_path: Path | None = None) -> RuntimeSettings:
    load_dotenv()
    y = _load_yaml_defaults(defaults_path)

    openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("CHATGPT_API_KEY")
    model = os.getenv("PAGEINDEX_MODEL") or y.get("model") or "gpt-4o-2024-11-20"
    pdf_parser = os.getenv("CHUNKSMITH_PDF_PARSER") or y.get("pdf_parser") or "PyPDF2"
    max_tokens = int(os.getenv("CHUNKSMITH_MAX_TOKENS_PER_CHUNK") or y.get("max_tokens_per_chunk") or 20000)
    overlap = int(os.getenv("CHUNKSMITH_OVERLAP_PAGES") or y.get("overlap_pages") or 1)
    gen_doc = _env_bool("CHUNKSMITH_GENERATE_DOC_SUMMARY", bool(y.get("generate_doc_summary", False)))

    azure_endpoint = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip() or None
    azure_key = (os.getenv("AZURE_OPENAI_API_KEY") or "").strip() or None
    # Azure deployment name — same precedence as app/core/config (AZURE_OPENAI_CHAT_MODEL).
    azure_deployment = (
        (os.getenv("AZURE_OPENAI_CHAT_MODEL") or "").strip()
        or (os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT") or "").strip()
        or None
    )

    return RuntimeSettings(
        openai_api_key=openai_key,
        pageindex_model=model,
        pdf_parser=pdf_parser.strip(),
        max_tokens_per_chunk=max_tokens,
        overlap_pages=max(0, overlap),
        generate_doc_summary=gen_doc,
        azure_openai_endpoint=azure_endpoint,
        azure_openai_api_key=azure_key,
        azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_openai_chat_model=azure_deployment,
        hf_token=(os.getenv("HF_TOKEN") or "").strip() or None,
        rag_model=os.getenv("RAG_MODEL") or model,
    )
