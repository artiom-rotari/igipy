from io import BytesIO
from struct import Struct
from typing import ClassVar, Literal, Self

from pydantic import NonNegativeInt

from igipy.core.formats import ilff


class AICHChunk(ilff.Chunk):
    node_count: NonNegativeInt
    version: Literal[1]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"AICH")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        node_count, version = Struct("<2I").unpack(content)
        return {"node_count": node_count, "version": version}

    def model_dump_content(self) -> bytes:
        return Struct("<2I").pack(self.node_count, self.version)


class AICNChunk(ilff.Chunk):
    node_ptr: NonNegativeInt
    prev_node_ptr: NonNegativeInt
    flags_1: NonNegativeInt
    flags_2: NonNegativeInt
    coverage_data: list[NonNegativeInt]

    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"AICN")

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        values = Struct("<36I").unpack(content)
        return {
            "node_ptr": values[0],
            "prev_node_ptr": values[1],
            "flags_1": values[2],
            "flags_2": values[3],
            "coverage_data": list(values[4:]),
        }

    def model_dump_content(self) -> bytes:
        return Struct("<36I").pack(
            self.node_ptr,
            self.prev_node_ptr,
            self.flags_1,
            self.flags_2,
            *self.coverage_data,
        )


class DATGraphCover(ilff.ILFF):
    """Graphcover DAT — AI cover/visibility data in ILFF container."""

    chunk_mapping: ClassVar[dict[bytes, type[ilff.Chunk]]] = {
        b"AICH": AICHChunk,
        b"AICN": AICNChunk,
    }

    aich: AICHChunk
    nodes: list[AICNChunk]

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header, content_type, content = super().model_validate_chunks(stream)

        if content_type != b"AICC":
            raise ValueError(f"Expected content type b'AICC', got {content_type!r}")

        aich_chunks = [c for c in content if isinstance(c, AICHChunk)]
        aicn_chunks = [c for c in content if isinstance(c, AICNChunk)]

        if len(aich_chunks) != 1:
            raise ValueError(f"Expected 1 AICH chunk, got {len(aich_chunks)}")

        aich = aich_chunks[0]

        if aich.node_count != len(aicn_chunks):
            raise ValueError(f"AICH node_count {aich.node_count} != AICN chunk count {len(aicn_chunks)}")

        return cls(header=header, content_type=content_type, aich=aich, nodes=aicn_chunks)

    def model_dump_stream(self) -> tuple[BytesIO, str]:
        stream = BytesIO()
        header_struct = Struct("4s3I")

        # ILFF header placeholder (filled in at the end)
        stream.write(b"\x00" * header_struct.size)
        stream.write(self.content_type)
        _write_padding(stream, self.header.alignment)

        # Write chunks: AICH followed by AICN nodes
        chunks: list[ilff.Chunk] = [self.aich, *self.nodes]

        for i, chunk in enumerate(chunks):
            chunk_start = stream.tell()
            stream.write(b"\x00" * header_struct.size)
            _write_padding(stream, chunk.header.alignment)
            content = chunk.model_dump_content()
            stream.write(content)
            _write_padding(stream, chunk.header.alignment)
            chunk_end = stream.tell()

            offset = 0 if i == len(chunks) - 1 else (chunk_end - chunk_start)
            stream.seek(chunk_start)
            stream.write(header_struct.pack(chunk.header.fourcc, len(content), chunk.header.alignment, offset))
            stream.seek(chunk_end)

        # Fill in ILFF header (length = total file size)
        total_length = stream.tell()
        stream.seek(0)
        stream.write(header_struct.pack(b"ILFF", total_length, self.header.alignment, self.header.offset))
        stream.seek(0)
        return stream, ".dat"


def _write_padding(stream: BytesIO, alignment: int) -> None:
    if alignment:
        padding = (alignment - stream.tell() % alignment) % alignment
        stream.write(b"\x00" * padding)
