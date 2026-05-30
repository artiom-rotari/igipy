import zipfile
from collections.abc import Generator
from io import BytesIO
from pathlib import Path

from pydantic import field_validator

from igipy.core.manager import BaseManager, PosixPath


class IGI2Manager(BaseManager):
    game_dir: PosixPath = Path("C:/Games/ProjectIGI2")
    collect_path: PosixPath = Path("igi2_collected.zip")
    convert_path: PosixPath = Path("igi2_converted.zip")

    # noinspection PyNestedDecorators
    @field_validator("game_dir", mode="after")
    @classmethod
    def is_game_dir(cls, value: Path) -> Path:
        if not value.is_dir():
            raise ValueError(f"{value.as_posix()} is not a directory")

        return value

    def read_from_collect_zip(self, patterns: list[str]) -> Generator[tuple[BytesIO, Path, Path]]:
        with zipfile.ZipFile(self.collect_path, "r") as zip_file:
            for file_info in zip_file.infolist():
                source_path = Path(file_info.filename)

                if any(source_path.match(pattern) for pattern in patterns):
                    source_stream = BytesIO(zip_file.read(file_info))
                    yield source_stream, source_path, self.collect_path

    def read_all_wav(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect_zip(patterns=["**/*.wav"])

    def read_all_qvm(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect_zip(patterns=["**/*.qvm"])

    def read_all_tex(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect_zip(patterns=["**/*.tex", "**/*.spr", "**/*.pic"])

    def read_all_mef(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect_zip(patterns=["**/*.mef"])

    def read_all_mtp(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect_zip(patterns=["**/*.mtp"])

    def read_all_syn(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect_zip(patterns=["**/*.syn"])

    def read_all_iff(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect_zip(patterns=["**/*.iff"])

    def read_all_olm(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect_zip(patterns=["**/*.olm"])
