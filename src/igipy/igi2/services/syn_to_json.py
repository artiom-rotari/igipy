import json
from io import BytesIO
from pathlib import Path

from igipy.igi2.formats.syn import SYN


def syn_to_json(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_path: Path | None = source_path.with_suffix(".json") if source_path is not None else None
    syn_instance = SYN.model_validate_stream(source_io)
    rounded = [round(s, 4) for s in syn_instance.samples]
    target_io = BytesIO()
    target_io.write(json.dumps(rounded, indent=2).encode("utf-8"))
    target_io.seek(0)
    return target_io, target_path
