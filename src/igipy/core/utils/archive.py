import zipfile
from collections.abc import Generator
from io import BytesIO
from pathlib import Path, PurePosixPath
from types import TracebackType
from typing import Self
from zipfile import ZipFile

# Suffixes whose contents are large and/or already compressed. Storing them uncompressed
# (ZIP_STORED) keeps writes cheap and reduces corruption risk if a write is interrupted; small
# textual outputs (json, qsc, fnt, ...) still benefit from ZIP_DEFLATED.
STORED_SUFFIXES: frozenset[str] = frozenset(
    {".wav", ".mp3", ".tga", ".bmp", ".jpg", ".jpeg", ".avi", ".fbx"}
)


def compression_for(name: str) -> int:
    """Pick a per-entry zip compression method based on the member suffix."""
    suffix = PurePosixPath(name).suffix.lower()
    return zipfile.ZIP_STORED if suffix in STORED_SUFFIXES else zipfile.ZIP_DEFLATED


def iter_source_entries(source_path: Path, is_zip: bool) -> Generator[tuple[PurePosixPath, BytesIO]]:
    """Yield ``(member_name, stream)`` pairs from a zip archive or a directory tree.

    The duality is driven by ``is_zip``: when True the source is read as a zip archive, otherwise
    ``source_path`` is walked recursively and each file becomes one entry whose name is the path
    relative to ``source_path``.
    """
    if is_zip:
        with ZipFile(source_path, "r") as zip_file:
            for file_info in zip_file.infolist():
                if file_info.is_dir():
                    continue
                yield PurePosixPath(file_info.filename), BytesIO(zip_file.read(file_info))
        return

    for item in sorted(source_path.rglob("*")):
        if not item.is_file():
            continue
        relative_path = item.relative_to(source_path)
        yield PurePosixPath(relative_path.as_posix()), BytesIO(item.read_bytes())


def existing_destination_names(destination_path: Path, is_zip: bool) -> set[str]:
    """Return the set of member names already present at the destination (for skip detection)."""
    if not destination_path.exists():
        return set()

    if is_zip:
        with ZipFile(destination_path, "r") as zip_file:
            return set(zip_file.namelist())

    return {item.relative_to(destination_path).as_posix() for item in destination_path.rglob("*") if item.is_file()}


class ArchiveWriter:
    """Write ``(name, data)`` entries to a zip archive or a directory tree, driven by ``is_zip``.

    In dry mode no bytes are written; the writer still behaves like a sink so callers can run their
    full reporting path without side effects. Use as a context manager so the underlying zip handle
    is always closed.
    """

    def __init__(self, destination_path: Path, is_zip: bool, dry: bool = False, overwrite: bool = False) -> None:
        self.destination_path = destination_path
        self.is_zip = is_zip
        self.dry = dry
        self.overwrite = overwrite
        self._zip_file: ZipFile | None = None

        if self.dry:
            return

        if self.is_zip:
            # overwrite rebuilds the archive from scratch (collect); otherwise append so repeated
            # convert runs can accumulate entries into an existing archive.
            mode = "w" if overwrite or not destination_path.exists() else "a"
            self._zip_file = ZipFile(destination_path, mode, zipfile.ZIP_DEFLATED)
        else:
            destination_path.mkdir(parents=True, exist_ok=True)

    def write(self, name: str, data: bytes) -> None:
        if self.dry:
            return

        if self.is_zip:
            assert self._zip_file is not None  # noqa: S101
            self._zip_file.writestr(name, data, compress_type=compression_for(name))
        else:
            target_path = self.destination_path / name
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(data)

    def close(self) -> None:
        if self._zip_file is not None:
            self._zip_file.close()
            self._zip_file = None

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
