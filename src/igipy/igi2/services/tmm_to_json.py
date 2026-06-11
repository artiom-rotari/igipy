import json
from io import BytesIO
from pathlib import Path

from igipy.igi2.formats.tmm import TMM


def tmm_to_json(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_path: Path | None = source_path.with_suffix(".tmm.json") if source_path is not None else None
    tmm_instance = TMM.model_validate_stream(source_io)

    payload = {
        "width": tmm_instance.header.width,
        "height": tmm_instance.header.height,
        "content": tmm_instance.content_values,
    }

    target_io = BytesIO()
    target_io.write(json.dumps(payload, indent=2).encode("utf-8"))
    target_io.seek(0)
    return target_io, target_path
