from io import BytesIO
from struct import unpack_from
from typing import ClassVar, Self

from pydantic import NonNegativeInt

from igipy.igi2.formats.form import FORM, FORMChunk, FORMChunkHeader, FORMRawChunk


def _parse_string_table(content: bytes) -> tuple[int, list[str]]:
    count = unpack_from("<I", content, 0)[0]
    strings = [s.decode("ascii") for s in content[4:].split(b"\x00") if s]
    return count, strings


# noinspection DuplicatedCode
class BANMChunk(FORMChunk):
    count: NonNegativeInt
    names: list[str]

    @classmethod
    def model_validate_content(cls, header: FORMChunkHeader, content: bytes) -> Self:
        count, names = _parse_string_table(content)
        return cls(header=header, count=count, names=names)


class SNDSChunk(FORMChunk):
    count: NonNegativeInt
    names: list[str]

    @classmethod
    def model_validate_content(cls, header: FORMChunkHeader, content: bytes) -> Self:
        count, names = _parse_string_table(content)
        return cls(header=header, count=count, names=names)


# noinspection DuplicatedCode
class SVOLChunk(FORMChunk):
    count: NonNegativeInt
    names: list[str]

    @classmethod
    def model_validate_content(cls, header: FORMChunkHeader, content: bytes) -> Self:
        count, names = _parse_string_table(content)
        return cls(header=header, count=count, names=names)


class MODSChunk(FORMChunk):
    count: NonNegativeInt
    names: list[str]

    @classmethod
    def model_validate_content(cls, header: FORMChunkHeader, content: bytes) -> Self:
        count, names = _parse_string_table(content)
        return cls(header=header, count=count, names=names)


class VNAMChunk(FORMChunk):
    count: NonNegativeInt
    offsets: list[NonNegativeInt]
    names: list[str]

    @classmethod
    def model_validate_content(cls, header: FORMChunkHeader, content: bytes) -> Self:
        count = unpack_from("<I", content, 0)[0]
        offsets = list(unpack_from(f"<{count}I", content, 4)) if count > 0 else []
        str_start = 4 + count * 4
        names = [s.decode("ascii") for s in content[str_start:].split(b"\x00") if s]
        return cls(header=header, count=count, offsets=offsets, names=names)


class INSTChunk(FORMRawChunk):
    @classmethod
    def model_validate_content(cls, header: FORMChunkHeader, content: bytes) -> Self:
        return cls(header=header, content=content)


class TEXFChunk(FORMChunk):
    count: NonNegativeInt
    names: list[str]

    @classmethod
    def model_validate_content(cls, header: FORMChunkHeader, content: bytes) -> Self:
        count, names = _parse_string_table(content)
        return cls(header=header, count=count, names=names)


class PALFChunk(FORMChunk):
    value: NonNegativeInt

    @classmethod
    def model_validate_content(cls, header: FORMChunkHeader, content: bytes) -> Self:
        value = unpack_from("<I", content, 0)[0]
        return cls(header=header, value=value)


class GTTChunk(FORMChunk):
    count: NonNegativeInt
    entries: list[tuple[NonNegativeInt, int]]

    @classmethod
    def model_validate_content(cls, header: FORMChunkHeader, content: bytes) -> Self:
        count = unpack_from("<I", content, 0)[0]
        entries = []

        for i in range(count):
            a, b = unpack_from("<Ii", content, 4 + i * 8)
            entries.append((a, b))

        return cls(header=header, count=count, entries=entries)


class MTP(FORM):
    chunk_mapping: ClassVar[dict[bytes, type[FORMChunk]]] = {
        b"BANM": BANMChunk,
        b"SNDS": SNDSChunk,
        b"SVOL": SVOLChunk,
        b"MODS": MODSChunk,
        b"VNAM": VNAMChunk,
        b"INST": INSTChunk,
        b"TEXF": TEXFChunk,
        b"PALF": PALFChunk,
        b"GTT ": GTTChunk,
    }

    banm: BANMChunk
    snds: SNDSChunk
    svol: SVOLChunk
    mods: MODSChunk
    vnam: VNAMChunk
    inst: INSTChunk
    texf: TEXFChunk
    palf: PALFChunk
    gtt: GTTChunk

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header, chunks = super().model_validate_chunks(stream)

        if header.content_type != b"MTP ":
            raise ValueError(f"Expected content type MTP , got {header.content_type}")

        field_mapping: dict[type[FORMChunk], str] = {
            BANMChunk: "banm",
            SNDSChunk: "snds",
            SVOLChunk: "svol",
            MODSChunk: "mods",
            VNAMChunk: "vnam",
            INSTChunk: "inst",
            TEXFChunk: "texf",
            PALFChunk: "palf",
            GTTChunk: "gtt",
        }

        values: dict[str, FORMChunk] = {}

        for chunk in chunks:
            field_name = field_mapping.get(type(chunk))

            if field_name is None:
                raise ValueError(f"Unknown chunk type: {chunk.header.fourcc}")

            if field_name in values:
                raise ValueError(f"Duplicate chunk: {chunk.header.fourcc}")

            values[field_name] = chunk

        return cls(header=header, **values)
