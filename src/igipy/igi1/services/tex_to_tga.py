from io import BytesIO

from igipy.core.formats.tex import TEX, TEX02, TEX07, TEX09, TEX11
from igipy.core.formats.tga import TGA


def tex_to_tga(instance: TEX) -> tuple[BytesIO, str]:
    """Convert a TEX texture instance to a TGA image."""
    variant = instance.variant

    if isinstance(variant, TEX02):
        return TGA.from_raw_bytes(
            width=variant.header.width,
            height=variant.header.height,
            content=variant.content.bitmap,
            pixel_format={2: "ARGB1555", 3: "ARGB8888", 67: "ARGB8888"}[variant.header.mode],
            bottom_to_top=True,
        ).model_dump_stream()

    if isinstance(variant, (TEX07, TEX09)):
        bitmap = variant.bitmap
        return TGA.from_raw_bytes(
            width=bitmap.shape[1],
            height=bitmap.shape[0],
            content=bitmap.tobytes(),
            pixel_format={2: "ARGB1555", 3: "ARGB8888", 67: "ARGB8888"}[variant.header.mode],
            bottom_to_top=True,
        ).model_dump_stream()

    if isinstance(variant, TEX11):
        return TGA.from_raw_bytes(
            width=variant.header.width,
            height=variant.header.height,
            content=variant.content[0].bitmap,
            pixel_format={2: "ARGB1555", 3: "ARGB8888", 67: "ARGB8888"}[variant.header.mode],
            bottom_to_top=True,
        ).model_dump_stream()

    raise ValueError(f"Unsupported TEX variant: {type(variant)}")
