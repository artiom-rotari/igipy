from io import BytesIO
from struct import unpack_from
from typing import ClassVar, Self

from pydantic import BaseModel, NonNegativeInt

from igipy.igi2.formats.form import FORM, FORMChunk, FORMChunkHeader


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


class INSTRecord(BaseModel):
    """One model's texture assignment: a model index and its texture indices.

    ``model_index`` indexes the ``MODS`` model-name table; each entry of
    ``texture_indices`` indexes the ``TEXF`` texture-name table. Together they encode the same
    per-model texture list as the machine-generated text ``.dat`` sibling, in material order.
    """

    model_index: NonNegativeInt
    texture_indices: list[NonNegativeInt]


class INSTChunk(FORMChunk):
    """Per-model texture-assignment records.

    Flat record stream: ``[model_index uint32, texture_count uint32, texture_index uint32 x count]``
    repeated until the chunk is exhausted (verified to consume the chunk exactly, with one record
    per ``MODS`` entry). Resolve readable names via ``MTP.model_texture_table``.
    """

    records: list[INSTRecord]

    @classmethod
    def model_validate_content(cls, header: FORMChunkHeader, content: bytes) -> Self:
        records: list[INSTRecord] = []
        offset = 0

        while offset + 8 <= len(content):
            model_index, texture_count = unpack_from("<II", content, offset)
            offset += 8

            if offset + 4 * texture_count > len(content):
                break

            texture_indices = list(unpack_from(f"<{texture_count}I", content, offset)) if texture_count else []
            offset += 4 * texture_count
            records.append(INSTRecord(model_index=model_index, texture_indices=texture_indices))

        return cls(header=header, records=records)


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

    def model_texture_table(self) -> dict[str, list[str]]:
        """Build the ``{model_name: [texture_name, ...]}`` table from the binary chunks.

        Joins the ``INST`` records against the ``MODS`` and ``TEXF`` name tables. This is the
        binary equivalent of the machine-generated text ``.dat`` table; texture names are returned
        as stored (pixel-format suffixes like ``_argb8888`` are kept). Records or indices that fall
        outside the name tables are skipped rather than raising, so partially-truncated files still
        yield whatever resolved cleanly.
        """
        table: dict[str, list[str]] = {}

        for record in self.inst.records:
            if record.model_index >= len(self.mods.names):
                continue

            model_name = self.mods.names[record.model_index]
            table[model_name] = [
                self.texf.names[texture_index]
                for texture_index in record.texture_indices
                if texture_index < len(self.texf.names)
            ]

        return table
