from io import BytesIO
from pathlib import Path

# Extensions copied verbatim from the collect source to the convert destination (no conversion).
RAW_PATTERNS: list[str] = ["*.mp3", "*.bmp", "*.jpg", "*.tga", "*.json"]


def copy_raw(source_stream: BytesIO, source_path: Path | None) -> tuple[BytesIO, Path | None]:
    """Pass-through converter: emit the source bytes unchanged at the same member path."""
    return source_stream, source_path
