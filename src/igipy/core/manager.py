from collections.abc import Generator
from io import BytesIO
from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel, PlainSerializer, model_validator

from igipy.core.utils.archive import iter_source_entries

PosixPath = Annotated[Path, PlainSerializer(lambda value: value.as_posix(), return_type=str, when_used="json")]


class BaseManager(BaseModel):
    collect_is_zip: bool = False
    convert_is_zip: bool = False

    @model_validator(mode="after")
    def validate_zip_path_suffixes(self) -> Self:
        # When a path is declared as a zip archive, it must carry the ".zip" suffix; when it is a
        #  directory, no suffix is required. The collect/convert paths live on the game-specific
        # subclasses, so they are read defensively here to keep BaseManager standalone-valid.
        collect_path: Path | None = getattr(self, "collect_path", None)
        if self.collect_is_zip and collect_path is not None and collect_path.suffix != ".zip":
            raise ValueError(
                f"collect_path must end with '.zip' when collect_is_zip is true: {collect_path.as_posix()}"
            )

        convert_path: Path | None = getattr(self, "convert_path", None)
        if self.convert_is_zip and convert_path is not None and convert_path.suffix != ".zip":
            raise ValueError(
                f"convert_path must end with '.zip' when convert_is_zip is true: {convert_path.as_posix()}"
            )

        return self

    def read_from_collect(self, patterns: list[str]) -> Generator[tuple[BytesIO, Path, Path]]:
        """Yield "(stream, source_path, collect_origin)" for matching files in the collect source.

        The collect source is read as a zip archive or a directory tree depending on
        "collect_is_zip"; pattern matching uses "Path.match" so glob patterns like "**/*.wav"
        keep working regardless of the source shape.
        """
        collect_path: Path = getattr(self, "collect_path")  # noqa: B009
        for member_name, source_stream in iter_source_entries(collect_path, self.collect_is_zip):
            source_path = Path(member_name.as_posix())
            if any(source_path.match(pattern) for pattern in patterns):
                yield source_stream, source_path, collect_path
