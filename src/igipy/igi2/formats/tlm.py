from io import BytesIO
from struct import Struct
from typing import ClassVar, Literal, Self

import numpy as np
from pydantic import NonNegativeInt

from igipy.core.base import FileModel, StructModel


class TLMHeader(StructModel):
    """TLM header — 44 bytes total (32 common + 12 extra)."""

    struct: ClassVar[Struct] = Struct("<f7II2I")

    terrain_scale: float
    year: NonNegativeInt
    month: NonNegativeInt
    day: NonNegativeInt
    hour: NonNegativeInt
    minute: NonNegativeInt
    second: NonNegativeInt
    unknown: NonNegativeInt
    type: Literal[3]
    width: NonNegativeInt
    height: NonNegativeInt


# noinspection DuplicatedCode
class TLM(FileModel):
    """Terrain Light Map — RGBA lightmap."""

    header: TLMHeader
    content: bytes

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header = TLMHeader.model_validate_stream(stream)
        expected_size = header.width * header.height * 4
        content = stream.read(expected_size)

        if len(content) != expected_size:
            raise ValueError(f"Expected {expected_size} bytes, got {len(content)}")

        if stream.read(1) != b"":
            raise ValueError("Expected end of stream")

        return cls(header=header, content=content)

    def model_dump_stream(self) -> tuple[BytesIO, str]:
        stream = BytesIO()
        h = self.header
        stream.write(
            TLMHeader.struct.pack(
                h.terrain_scale,
                h.year,
                h.month,
                h.day,
                h.hour,
                h.minute,
                h.second,
                h.unknown,
                h.type,
                h.width,
                h.height,
            )
        )
        stream.write(self.content)
        stream.seek(0)
        return stream, ".tlm"

    @property
    def bgra(self) -> bytes:
        """BGRA pixel data (swapped from stored RGBA)."""
        rgba = np.frombuffer(self.content, dtype=np.uint8).reshape(-1, 4)
        return rgba[:, [2, 1, 0, 3]].tobytes()
