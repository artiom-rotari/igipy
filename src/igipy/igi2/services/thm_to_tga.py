from io import BytesIO
from pathlib import Path

from igipy.core.formats.tga import TGA
from igipy.igi2.formats.thm import THM


def thm_to_tga(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_path: Path | None = source_path.with_suffix(".thm.tga") if source_path is not None else None
    thm_instance = THM.model_validate_stream(source_io)

    tga_instance = TGA.from_raw_bytes(
        width=thm_instance.header.width,
        height=thm_instance.header.height,
        content=thm_instance.bgra,
        pixel_format="ARGB8888",
        bottom_to_top=True,
    )
    target_io, _ = tga_instance.model_dump_stream()
    return target_io, target_path
