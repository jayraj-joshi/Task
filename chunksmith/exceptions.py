"""Domain-specific errors for the chunksmith outline pipeline."""


class ChunksmithError(Exception):
    """Base error for this package."""


class PdfLoadError(ChunksmithError):
    """Failed to open or read a PDF."""


class OutlineExtractionError(ChunksmithError):
    """LLM returned unusable output or finish_reason was not ``finished``."""
