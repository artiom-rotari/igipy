from io import BytesIO
from struct import Struct
from typing import ClassVar, Literal, Self, TypeVar

from pydantic import Field, NonNegativeInt

from igipy.core.base import StructModel
from igipy.core.formats import ilff

T = TypeVar("T", bound=ilff.Chunk)


def get_chunk_by_type(chunks: list[ilff.Chunk], chunk_type: type[T]) -> T:  # noqa: UP047
    for c in chunks:
        if isinstance(c, chunk_type):
            return c
    raise KeyError(chunk_type)


class FNTHChunk(ilff.Chunk):
    version: NonNegativeInt
    num_glyphs: NonNegativeInt
    cell_height: NonNegativeInt
    unknown_01: NonNegativeInt
    unknown_02: NonNegativeInt
    unknown_03: NonNegativeInt

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"FNTH")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        values = Struct("<6I").unpack(content)
        return dict(
            zip(
                ["version", "num_glyphs", "cell_height", "unknown_01", "unknown_02", "unknown_03"],
                values,
                strict=True,
            )
        )

    def model_dump_content(self) -> bytes:
        return Struct("<6I").pack(
            self.version,
            self.num_glyphs,
            self.cell_height,
            self.unknown_01,
            self.unknown_02,
            self.unknown_03,
        )


class GlyphMetric(StructModel):
    struct: ClassVar[Struct] = Struct("<5f2H2H2H2I")

    v_top: float = Field(description="Top V coordinate (normalized 0-1)")
    u_left: float = Field(description="Left U coordinate (normalized 0-1)")
    v_offset: float = Field(description="Vertical offset (normalized 0-1)")
    u_right: float = Field(description="Right U coordinate (normalized 0-1)")
    v_bottom: float = Field(description="Bottom V coordinate (normalized 0-1)")
    pad_0: NonNegativeInt = Field(description="Padding (always 0)")
    width: NonNegativeInt = Field(description="Glyph width in pixels")
    height: NonNegativeInt = Field(description="Glyph height in pixels")
    advance_x: NonNegativeInt = Field(description="Horizontal advance in pixels")
    height_2: NonNegativeInt = Field(description="Glyph height (duplicate)")
    pad_1: NonNegativeInt = Field(description="Padding (always 0)")
    pad_2: NonNegativeInt = Field(description="Padding (usually 0)")
    unknown_01: int = Field(description="Unknown flag or kerning value")


class ANMFChunk(ilff.Chunk):
    glyphs: list[GlyphMetric]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"ANMF")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"glyphs": GlyphMetric.unpack_many(content)}

    def model_dump_content(self) -> bytes:
        return b"".join(
            GlyphMetric.struct.pack(
                g.v_top,
                g.u_left,
                g.v_offset,
                g.u_right,
                g.v_bottom,
                g.pad_0,
                g.width,
                g.height,
                g.advance_x,
                g.height_2,
                g.pad_1,
                g.pad_2,
                g.unknown_01,
            )
            for g in self.glyphs
        )


class TRN2Chunk(ilff.Chunk):
    char_codes: list[int]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"TRN2")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        count = len(content) // 2
        codes = list(Struct(f"<{count}H").unpack(content))
        return {"char_codes": codes}

    def model_dump_content(self) -> bytes:
        count = len(self.char_codes)
        return Struct(f"<{count}H").pack(*self.char_codes)


class TEXHChunk(ilff.Chunk):
    format: NonNegativeInt
    unknown_01: NonNegativeInt
    unknown_02: NonNegativeInt
    unknown_03: NonNegativeInt
    unknown_04: NonNegativeInt
    unknown_05: NonNegativeInt
    unknown_06: NonNegativeInt
    width: NonNegativeInt
    height: NonNegativeInt
    width_2: NonNegativeInt
    height_2: NonNegativeInt
    pixel_depth: NonNegativeInt

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"TEXH")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        values = Struct("<12H").unpack(content)
        return dict(
            zip(
                [
                    "format",
                    "unknown_01",
                    "unknown_02",
                    "unknown_03",
                    "unknown_04",
                    "unknown_05",
                    "unknown_06",
                    "width",
                    "height",
                    "width_2",
                    "height_2",
                    "pixel_depth",
                ],
                values,
                strict=True,
            )
        )

    def model_dump_content(self) -> bytes:
        return Struct("<12H").pack(
            self.format,
            self.unknown_01,
            self.unknown_02,
            self.unknown_03,
            self.unknown_04,
            self.unknown_05,
            self.unknown_06,
            self.width,
            self.height,
            self.width_2,
            self.height_2,
            self.pixel_depth,
        )


class BODYChunk(ilff.RawChunk):
    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"BODY")


class FNT(ilff.ILFF):
    chunk_mapping: ClassVar[dict[bytes, type[ilff.Chunk]]] = {
        b"FNTH": FNTHChunk,
        b"ANMF": ANMFChunk,
        b"TRN2": TRN2Chunk,
        b"TEXH": TEXHChunk,
        b"BODY": BODYChunk,
    }

    content_type: Literal[b"FONT"] = Field(description="Content type")
    font_header: FNTHChunk
    glyph_metrics: ANMFChunk
    char_mapping: TRN2Chunk
    texture_header: TEXHChunk
    texture_body: BODYChunk

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header, content_type, chunks = super().model_validate_chunks(stream)

        if content_type != b"FONT":
            raise ValueError(f"Expected FONT content type, got {content_type}")

        return cls(
            header=header,
            content_type=content_type,
            font_header=get_chunk_by_type(chunks, FNTHChunk),
            glyph_metrics=get_chunk_by_type(chunks, ANMFChunk),
            char_mapping=get_chunk_by_type(chunks, TRN2Chunk),
            texture_header=get_chunk_by_type(chunks, TEXHChunk),
            texture_body=get_chunk_by_type(chunks, BODYChunk),
        )

    def model_dump_stream(self) -> tuple[BytesIO, str]:
        stream = BytesIO()

        h = self.header
        stream.write(ilff.ChunkHeader.struct.pack(h.fourcc, h.length, h.alignment, h.offset))

        stream.write(self.content_type)
        self._write_padding(stream, h.alignment)

        chunks = [self.font_header, self.glyph_metrics, self.char_mapping, self.texture_header, self.texture_body]
        for chunk in chunks:
            ch = chunk.header
            stream.write(ilff.ChunkHeader.struct.pack(ch.fourcc, ch.length, ch.alignment, ch.offset))
            self._write_padding(stream, ch.alignment)
            stream.write(chunk.model_dump_content())
            self._write_padding(stream, ch.alignment)

        stream.seek(0)
        return stream, ".fnt"

    @staticmethod
    def _write_padding(stream: BytesIO, alignment: int) -> None:
        if alignment:
            padding = (alignment - stream.tell() % alignment) % alignment
            stream.write(b"\x00" * padding)
