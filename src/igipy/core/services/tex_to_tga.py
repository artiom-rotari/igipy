from io import BytesIO
from pathlib import Path

from igipy.core.formats.tex import TEX, TEX02, TEX07, TEX09, TEX11
from igipy.core.formats.tga import TGA


def tex_to_tga(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_path: Path | None = source_path.with_suffix(".tga") if source_path is not None else None
    tex_instance = TEX.model_validate_stream(source_io)

    if isinstance(tex_instance.variant, TEX02):
        tga_instance = TGA.from_raw_bytes(
            width=tex_instance.variant.header.width,
            height=tex_instance.variant.header.height,
            content=tex_instance.variant.content.bitmap,
            pixel_format={2: "ARGB1555", 3: "ARGB8888", 67: "ARGB8888"}[tex_instance.variant.header.mode],
            bottom_to_top=True,
        )

    elif isinstance(tex_instance.variant, (TEX07, TEX09)):
        tga_instance = TGA.from_raw_bytes(
            width=tex_instance.variant.bitmap.shape[1],
            height=tex_instance.variant.bitmap.shape[0],
            content=tex_instance.variant.bitmap.tobytes(),
            pixel_format={2: "ARGB1555", 3: "ARGB8888", 67: "ARGB8888"}[tex_instance.variant.header.mode],
            bottom_to_top=True,
        )

    elif isinstance(tex_instance.variant, TEX11):
        tga_instance = TGA.from_raw_bytes(
            width=tex_instance.variant.header.width,
            height=tex_instance.variant.header.height,
            content=tex_instance.variant.content[0].bitmap,
            pixel_format={2: "ARGB1555", 3: "ARGB8888", 67: "ARGB8888"}[tex_instance.variant.header.mode],
            bottom_to_top=True,
        )

    else:
        raise TypeError(f"Unsupported TEX variant: {type(tex_instance.variant)}")

    target_io, _ = tga_instance.model_dump_stream()

    return target_io, target_path
