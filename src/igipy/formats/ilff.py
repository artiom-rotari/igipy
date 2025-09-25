from abc import ABC
from io import BytesIO
from struct import Struct
from typing import ClassVar, Literal, Self

from pydantic import BaseModel, Field, NonNegativeInt

from igipy.formats.base import CLIFileModel, StructModel


class ChunkHeader(StructModel):
    struct: ClassVar[Struct] = Struct("4s3I")

    fourcc: bytes = Field(min_length=4, max_length=4, description="Chunk signature")
    length: NonNegativeInt = Field(description="Length of chunk")
    alignment: Literal[0, 4, 32] = Field(description="Padding calculation divisor")
    offset: NonNegativeInt = Field(description="Position of next chunk (0 if last)")

    def model_validate_padding(self, stream: BytesIO) -> bytes:
        padding = (self.alignment - stream.tell() % self.alignment) % self.alignment if self.alignment else 0
        padding_bytes = stream.read(padding)

        if padding_bytes not in {b"", b"\x00" * padding}:
            raise ValueError(f"Unexpected padding bytes: {padding_bytes}")

        return padding_bytes


class Chunk(BaseModel):
    meta_start: NonNegativeInt | None = Field(default=None, description="Meta information")
    meta_end: NonNegativeInt | None = Field(default=None, description="Meta information")
    header: ChunkHeader

    @classmethod
    def model_validate_stream(cls, stream: BytesIO, header: ChunkHeader) -> Self:
        cls.model_validate_header(header)
        header.model_validate_padding(stream)
        content = cls.model_validate_content(stream.read(header.length))
        header.model_validate_padding(stream)
        return cls(header=header, **content)

    @classmethod
    def model_validate_header(cls, header: ChunkHeader) -> None:
        pass

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        raise NotImplementedError


class RawChunk(Chunk):
    content: bytes

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": content}


class ILFFHeader(ChunkHeader):
    fourcc: Literal[b"ILFF"] = Field(description="Chunk signature")


class ILFF(CLIFileModel, ABC):
    chunk_mapping: ClassVar[dict[bytes, type[Chunk]]] = {}

    header: ILFFHeader
    content_type: bytes

    @classmethod
    def model_validate_chunks(cls, stream: BytesIO) -> tuple[ILFFHeader, bytes, list[Chunk]]:
        header = ILFFHeader.model_validate_stream(stream)
        content_type = stream.read(4)
        content = []
        header.model_validate_padding(stream)

        while stream.tell() < header.length:
            chunk_position_start = stream.tell()
            chunk_header = ChunkHeader.model_validate_stream(stream=stream)
            chunk = cls.model_validate_chunk(stream, chunk_header)
            chunk_position_end = stream.tell()
            chunk.meta_start = chunk_position_start
            chunk.meta_end = chunk_position_end

            content.append(chunk)

            if chunk.header.offset == 0:
                break

            if stream.tell() != chunk.meta_start + chunk.header.offset:
                raise ValueError(f"Unexpected position: {stream.tell()} not {chunk.meta_start + chunk.header.offset}")

        if stream.read(1) != b"":
            raise ValueError("Expected end of stream")

        return header, content_type, content

    @classmethod
    def model_validate_chunk(cls, stream: BytesIO, header: ChunkHeader) -> Chunk:
        return cls.chunk_mapping.get(header.fourcc, Chunk).model_validate_stream(stream, header)


def model_validate_header(header: ChunkHeader, fourcc: bytes) -> None:
    if header.fourcc != fourcc:
        raise ValueError(f"Expected {fourcc} header, got {header.fourcc}")
