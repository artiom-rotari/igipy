from collections.abc import Generator
from io import BytesIO
from pathlib import Path

from igipy.core.manager import BaseManager, PosixPath


class IGIxManager(BaseManager):
    """Manager for the early/beta IGI2 ("igix") resources.

    Unlike :class:`IGI1Manager` / :class:`IGI2Manager`, ``game_dir`` carries no
    ``is_game_dir`` validator: igix game collection is out of scope (the resources are
    used pre-collected from a directory tree), and a strict validator would make
    ``Config.model_validate_file()`` raise for every user whose igix path does not
    exist, breaking the whole CLI. The exporter reads from ``collect_path`` directly.
    """

    game_dir: PosixPath = Path("C:/Games/ProjectIGIx")
    collect_path: PosixPath = Path("igix_collected")
    convert_path: PosixPath = Path("igix_converted")

    def read_all_mef(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect(patterns=["**/*.mef"])

    def read_all_tex(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect(patterns=["**/*.tex", "**/*.spr", "**/*.pic"])

    def read_all_mtp(self) -> Generator[tuple[BytesIO, Path, Path | None]]:
        yield from self.read_from_collect(patterns=["**/*.mtp"])
