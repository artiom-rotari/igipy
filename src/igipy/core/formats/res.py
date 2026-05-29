from io import BytesIO
from typing import ClassVar, Literal, Self

from pydantic import Field

from igipy.core.base import FileIgnored
from igipy.core.formats import ilff


class NAMEChunk(ilff.RawChunk):
    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"NAME")

    def get_cleaned_content(self) -> str:
        return self.content.removesuffix(b"\x00").decode("latin1")


class BODYChunk(ilff.RawChunk):
    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"BODY")


class CSTRChunk(ilff.RawChunk):
    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"CSTR")

    def get_cleaned_content(self) -> str:
        return self.content.removesuffix(b"\x00").decode("latin1")


class PATHChunk(ilff.RawChunk):
    @classmethod
    def model_validate_header(cls, header: ilff.ChunkHeader) -> None:
        ilff.model_validate_header(header, fourcc=b"PATH")

    def get_cleaned_content(self) -> str:
        return self.content.removesuffix(b"\x00").decode("latin1")


class RES(ilff.ILFF):
    chunk_mapping: ClassVar[dict[bytes, type[ilff.Chunk]]] = {
        b"NAME": NAMEChunk,
        b"BODY": BODYChunk,
        b"CSTR": CSTRChunk,
        b"PATH": PATHChunk,
    }

    content_type: Literal[b"IRES"] = Field(description="Content type")
    content_pairs: list[tuple[NAMEChunk, BODYChunk]] | list[tuple[NAMEChunk, CSTRChunk]]
    content_paths: tuple[NAMEChunk, PATHChunk] | None = None

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header, content_type, chunks = super().model_validate_chunks(stream)

        if content_type != b"IRES":
            raise ValueError(f"Unknown content type: {content_type}")

        if not chunks:
            raise FileIgnored("Empty IRES container")

        content_pairs = list(zip(chunks[::2], chunks[1::2], strict=True))
        content_paths = content_pairs.pop(-1) if content_pairs[-1][1].header.fourcc == b"PATH" else None

        # noinspection PyTypeChecker
        return cls(
            header=header,
            content_type=content_type,
            content_pairs=content_pairs,
            content_paths=content_paths,
        )

    def model_dump_stream(self) -> tuple[BytesIO, str]:
        stream = BytesIO()

        h = self.header
        stream.write(ilff.ChunkHeader.struct.pack(h.fourcc, h.length, h.alignment, h.offset))

        stream.write(self.content_type)
        self._write_padding(stream, h.alignment)

        all_chunks: list[ilff.RawChunk] = []
        for chunk_a, chunk_b in self.content_pairs:
            all_chunks.extend([chunk_a, chunk_b])
        if self.content_paths is not None:
            all_chunks.extend(self.content_paths)

        for chunk in all_chunks:
            ch = chunk.header
            stream.write(ilff.ChunkHeader.struct.pack(ch.fourcc, ch.length, ch.alignment, ch.offset))
            self._write_padding(stream, ch.alignment)
            stream.write(chunk.model_dump_content())
            if ch.offset != 0:
                self._write_padding(stream, ch.alignment)

        stream.seek(0)
        return stream, ".res"

    @staticmethod
    def _write_padding(stream: BytesIO, alignment: int) -> None:
        if alignment:
            padding = (alignment - stream.tell() % alignment) % alignment
            stream.write(b"\x00" * padding)

    def what_is_inside(self) -> Literal["file", "text"]:
        if all(chunk.header.fourcc == b"BODY" for _, chunk in self.content_pairs):
            return "file"

        if all(chunk.header.fourcc == b"CSTR" for _, chunk in self.content_pairs):
            return "text"

        raise ValueError("Unknown file container type")
