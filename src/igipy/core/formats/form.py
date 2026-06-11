from io import BytesIO
from struct import Struct
from typing import Annotated, ClassVar, Self

from pydantic import BaseModel, Field, NonNegativeInt, PlainSerializer

from igipy.core.base import FileModel

FourCC = Annotated[bytes, Field(min_length=4, max_length=4), PlainSerializer(lambda v: v.decode("ascii").strip())]
RawBytes = Annotated[bytes, PlainSerializer(lambda v: v.hex())]


class FORMChunkHeader(BaseModel):
    struct: ClassVar[Struct] = Struct(">4sI")

    fourcc: FourCC
    length: NonNegativeInt

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        data = stream.read(cls.struct.size)

        if len(data) < cls.struct.size:
            raise ValueError(f"Not enough data for FORM chunk header: {len(data)} < {cls.struct.size}")

        fourcc, length = cls.struct.unpack(data)
        return cls(fourcc=fourcc, length=length)


class FORMChunk(BaseModel):
    header: FORMChunkHeader

    @classmethod
    def model_validate_stream(cls, stream: BytesIO, header: FORMChunkHeader) -> Self:
        content = stream.read(header.length)

        if len(content) < header.length:
            raise ValueError(f"Not enough data for chunk {header.fourcc}: {len(content)} < {header.length}")

        if header.length % 2 != 0:
            stream.read(1)

        return cls.model_validate_content(header, content)

    @classmethod
    def model_validate_content(cls, header: FORMChunkHeader, content: bytes) -> Self:
        raise NotImplementedError


class FORMRawChunk(FORMChunk):
    content: RawBytes

    @classmethod
    def model_validate_content(cls, header: FORMChunkHeader, content: bytes) -> Self:
        return cls(header=header, content=content)


class FORMHeader(BaseModel):
    struct: ClassVar[Struct] = Struct(">4sI4s")

    fourcc: FourCC
    length: NonNegativeInt
    content_type: FourCC

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        data = stream.read(cls.struct.size)

        if len(data) < cls.struct.size:
            raise ValueError(f"Not enough data for FORM header: {len(data)} < {cls.struct.size}")

        fourcc, length, content_type = cls.struct.unpack(data)

        if fourcc != b"FORM":
            raise ValueError(f"Expected FORM, got {fourcc}")

        return cls(fourcc=fourcc, length=length, content_type=content_type)


class FORM(FileModel):
    chunk_mapping: ClassVar[dict[bytes, type[FORMChunk]]] = {}

    header: FORMHeader

    @classmethod
    def model_validate_chunks(cls, stream: BytesIO) -> tuple[FORMHeader, list[FORMChunk]]:
        header = FORMHeader.model_validate_stream(stream)
        end_offset = 8 + header.length
        chunks = []

        while stream.tell() < end_offset:
            chunk_header = FORMChunkHeader.model_validate_stream(stream)
            chunk_cls = cls.chunk_mapping.get(chunk_header.fourcc, FORMRawChunk)
            chunk = chunk_cls.model_validate_stream(stream, chunk_header)
            chunks.append(chunk)

        return header, chunks
