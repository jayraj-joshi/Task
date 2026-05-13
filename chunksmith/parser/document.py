"""Load PDF pages as (text, token_length) pairs."""

from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from typing import List, Tuple, Union

import PyPDF2
import pymupdf

from chunksmith.config import RuntimeSettings
from chunksmith.exceptions import PdfLoadError
from chunksmith.llm_support.client import count_tokens

PdfSource = Union[str, Path, BytesIO]


def load_pdf_pages(source: PdfSource, settings: RuntimeSettings) -> List[Tuple[str, int]]:
    """
    Extract one string per PDF page and count tokens (for chunking).

    ``settings.pdf_parser`` must be ``PyPDF2`` or ``PyMuPDF``.
    """
    parser = settings.pdf_parser
    model = settings.pageindex_model

    if parser == "PyPDF2":
        return _load_pypdf2(source, model)
    if parser == "PyMuPDF":
        return _load_pymupdf(source, model)
    raise PdfLoadError(f"Unsupported pdf_parser: {parser!r} (use PyPDF2 or PyMuPDF)")


def _load_pypdf2(source: PdfSource, model: str) -> List[Tuple[str, int]]:
    if isinstance(source, (str, Path)):
        path = str(source)
        if not os.path.isfile(path):
            raise PdfLoadError(f"Not a file: {path}")
        reader = PyPDF2.PdfReader(path)
    else:
        reader = PyPDF2.PdfReader(source)
    out: List[Tuple[str, int]] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        out.append((text, count_tokens(text, model)))
    return out


def _load_pymupdf(source: PdfSource, model: str) -> List[Tuple[str, int]]:
    if isinstance(source, (str, Path)):
        path = str(source)
        if not os.path.isfile(path):
            raise PdfLoadError(f"Not a file: {path}")
        doc = pymupdf.open(path)
    else:
        doc = pymupdf.open(stream=source, filetype="pdf")
    try:
        out: List[Tuple[str, int]] = []
        for page in doc:
            text = page.get_text() or ""
            out.append((text, count_tokens(text, model)))
        return out
    finally:
        doc.close()
