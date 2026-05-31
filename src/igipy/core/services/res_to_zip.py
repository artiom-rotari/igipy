import json
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from igipy.core.formats.res import RES


def res_to_zip(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    instance = RES.model_validate_stream(source_io)
    target_io = BytesIO()
    types = {chunk_b.header.fourcc for _, chunk_b in instance.content_pairs}

    if types == {b"BODY"}:
        target_path = source_path.with_suffix(".zip") if source_path is not None else None
        with ZipFile(target_io, "w") as zip_stream:
            for chunk_a, chunk_b in instance.content_pairs:
                zip_stream.writestr(chunk_a.get_cleaned_content().removeprefix("LOCAL:"), chunk_b.content)
        return target_io, target_path

    if types == {b"CSTR"}:
        target_path = source_path.with_suffix(".json") if source_path is not None else None
        content = [
            {
                "key": chunk_a.get_cleaned_content().removeprefix("LOCAL:"),
                "value": chunk_b.get_cleaned_content(),
            }
            for chunk_a, chunk_b in instance.content_pairs
        ]
        target_io.write(json.dumps(content, indent=4).encode())
        return target_io, target_path

    raise ValueError(f"Unknown file container type: {types}")
