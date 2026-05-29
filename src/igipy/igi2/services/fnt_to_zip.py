from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from igipy.core.formats.tga import TGA
from igipy.igi2.formats.fnt import FNT


def fnt_to_zip(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_path: Path | None = source_path.with_suffix(".zip") if source_path is not None else None
    fnt_instance = FNT.model_validate_stream(source_io)

    tex_w = fnt_instance.texture_header.width
    tex_h = fnt_instance.texture_header.height
    cell_h = fnt_instance.font_header.cell_height
    num_glyphs = fnt_instance.font_header.num_glyphs

    bmfont_lines = [
        f'info face="IGI Font" size={cell_h} bold=0 italic=0 charset="" unicode=1'
        f" stretchH=100 smooth=1 aa=1 padding=0,0,0,0 spacing=1,1 outline=0",
        f"common lineHeight={cell_h} base={cell_h} scaleW={tex_w} scaleH={tex_h}"
        f" pages=1 packed=0 alphaChnl=1 redChnl=0 greenChnl=0 blueChnl=0",
        'page id=0 file="texture.tga"',
        f"chars count={num_glyphs}",
    ]

    for i, glyph in enumerate(fnt_instance.glyph_metrics.glyphs):
        char_code = fnt_instance.char_mapping.char_codes[i] if i < len(fnt_instance.char_mapping.char_codes) else 0
        x = int(glyph.u_left * tex_w)
        y = int(glyph.v_top * tex_h)
        bmfont_lines.append(
            f"char id={char_code:<6d}"
            f" x={x:<5d} y={y:<5d}"
            f" width={glyph.width:<5d} height={glyph.height:<5d}"
            f" xoffset={0:<5d} yoffset={0:<5d}"
            f" xadvance={glyph.advance_x:<5d}"
            f" page=0   chnl=15"
        )

    tga_instance = TGA.from_raw_bytes(
        width=tex_w,
        height=tex_h,
        content=fnt_instance.texture_body.content,
        pixel_format="ARGB8888",
        bottom_to_top=True,
    )
    tga_stream, _ = tga_instance.model_dump_stream()

    target_io = BytesIO()
    with ZipFile(target_io, "w") as zf:
        zf.writestr("font.fnt", "\n".join(bmfont_lines) + "\n")
        zf.writestr("texture.tga", tga_stream.getvalue())

    return target_io, target_path
