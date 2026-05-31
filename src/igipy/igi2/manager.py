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

    def read_all_wav(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect(patterns=["**/*.wav"])

    def read_all_qvm(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect(patterns=["**/*.qvm"])

    def read_all_tex(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect(patterns=["**/*.tex", "**/*.spr", "**/*.pic"])

    def read_all_mef(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect(patterns=["**/*.mef"])

    def read_all_mtp(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect(patterns=["**/*.mtp"])

    def read_all_syn(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect(patterns=["**/*.syn"])

    def read_all_iff(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect(patterns=["**/*.iff"])

    def read_all_olm(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect(patterns=["**/*.olm"])
