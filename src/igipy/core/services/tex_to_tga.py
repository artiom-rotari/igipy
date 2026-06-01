from io import BytesIO
from pathlib import Path

from igipy.core.formats.tex import TEX, TEX02, TEX07, TEX09, TEX11
from igipy.core.formats.tga import TGA


def tex_to_tga_image(instance: TEX) -> TGA:
    """Convert a parsed TEX texture into a TGA image (base level, byte-exact copy of the pixels).

    The source pixel bytes are copied verbatim into the TGA; only the variant-specific framing
    differs: TEX07/TEX09 reassemble their tile grid into a single bitmap, while TEX11 keeps the
    base mip level only. The mode-to-pixel-format mapping lives on the TEX model itself.
    """
    variant = instance.variant

    if isinstance(variant, TEX02):
        width = variant.header.width
        height = variant.header.height
        content = variant.content.bitmap
    elif isinstance(variant, (TEX07, TEX09)):
        bitmap = variant.bitmap
        width = bitmap.shape[1]
        height = bitmap.shape[0]
        content = bitmap.tobytes()
    elif isinstance(variant, TEX11):
        width = variant.header.width
        height = variant.header.height
        # base mip level only; higher mip levels are downscaled copies and are not exported
        content = variant.content[0].bitmap
    else:
        raise TypeError(f"Unsupported TEX variant: {type(variant)}")

    return TGA.from_raw_bytes(
        width=width,
        height=height,
        content=content,
        pixel_format=instance.pixel_format,
        bottom_to_top=True,
    )


def tex_to_tga(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_path: Path | None = source_path.with_suffix(".tga") if source_path is not None else None
    tex_instance = TEX.model_validate_stream(source_io)
    target_io, _ = tex_to_tga_image(tex_instance).model_dump_stream()
    return target_io, target_path
