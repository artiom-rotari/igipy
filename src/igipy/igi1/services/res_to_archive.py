import json
from io import BytesIO
from zipfile import ZipFile

from igipy.core.formats.res import RES


def res_to_archive(instance: RES) -> tuple[BytesIO, str]:
    """Convert a RES ILFF container to a ZIP (binary entries) or JSON (string entries)."""
    stream = BytesIO()
    types = {chunk_b.header.fourcc for _, chunk_b in instance.content_pairs}

    if types == {b"BODY"}:
        with ZipFile(stream, "w") as zip_stream:
            for chunk_a, chunk_b in instance.content_pairs:
                zip_stream.writestr(chunk_a.get_cleaned_content().removeprefix("LOCAL:"), chunk_b.content)
        return stream, ".zip"

    if types == {b"CSTR"}:
        content = [
            {
                "key": chunk_a.get_cleaned_content().removeprefix("LOCAL:"),
                "value": chunk_b.get_cleaned_content(),
            }
            for chunk_a, chunk_b in instance.content_pairs
        ]
        stream.write(json.dumps(content, indent=4).encode())
        return stream, ".json"

    raise ValueError(f"Unknown file container type: {types}")
