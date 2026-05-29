from io import BytesIO
from pathlib import Path

from igipy.core.formats.tga import TGA
from igipy.igi2.formats.tlm import TLM


def tlm_to_tga(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_path: Path | None = source_path.with_suffix(".tlm.tga") if source_path is not None else None
    tlm_instance = TLM.model_validate_stream(source_io)

    tga_instance = TGA.from_raw_bytes(
        width=tlm_instance.header.width,
        height=tlm_instance.header.height,
        content=tlm_instance.bgra,
        pixel_format="ARGB8888",
        bottom_to_top=True,
    )
    target_io, _ = tga_instance.model_dump_stream()
    return target_io, target_path
