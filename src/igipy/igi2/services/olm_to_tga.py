from io import BytesIO
from pathlib import Path

from igipy.core.formats.tga import TGA
from igipy.igi2.formats.olm import OLM


def olm_to_tga(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_path: Path | None = source_path.with_suffix(".olm.tga") if source_path is not None else None
    olm_instance = OLM.model_validate_stream(source_io)

    layer = olm_instance.layers[0]

    tga_instance = TGA.from_raw_bytes(
        width=layer.header.pixel_width,
        height=layer.header.pixel_height,
        content=layer.bgra,
        pixel_format="ARGB8888",
        bottom_to_top=True,
    )
    target_io, _ = tga_instance.model_dump_stream()
    return target_io, target_path
