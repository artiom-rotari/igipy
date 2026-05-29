from io import BytesIO
from pathlib import Path

from igipy.igi2.formats import DATGraphCover


def dat_graphcover_to_json(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_io: BytesIO = BytesIO()
    target_path: Path | None = source_path.with_suffix(".json") if source_path is not None else None
    instance = DATGraphCover.model_validate_stream(source_io)
    target_io.write(instance.model_dump_json(indent=2).encode("utf-8"))
    target_io.seek(0)
    return target_io, target_path
