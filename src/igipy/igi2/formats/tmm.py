from io import BytesIO
from struct import Struct
from typing import ClassVar, Literal, Self

import numpy as np
from pydantic import NonNegativeInt

from igipy.core.base import FileModel, StructModel

# Material index palette — 8 distinct BGRA colors for visualization
MATERIAL_PALETTE = np.array(
    [
        [0, 128, 0, 255],  # 0: green (grass)
        [43, 90, 139, 255],  # 1: brown (dirt)
        [128, 128, 128, 255],  # 2: gray (rock)
        [128, 178, 194, 255],  # 3: tan (sand)
        [255, 255, 255, 255],  # 4: white (snow)
        [85, 85, 85, 255],  # 5: dark gray (stone)
        [34, 139, 34, 255],  # 6: forest green (vegetation)
        [45, 82, 160, 255],  # 7: sienna (mud)
    ],
    dtype=np.uint8,
)


class TMMHeader(StructModel):
    """TMM header — 44 bytes total (32 common + 12 extra)."""

    struct: ClassVar[Struct] = Struct("<f7II2I")

    terrain_scale: float
    year: NonNegativeInt
    month: NonNegativeInt
    day: NonNegativeInt
    hour: NonNegativeInt
    minute: NonNegativeInt
    second: NonNegativeInt
    unknown: NonNegativeInt
    type: Literal[0]
    width: NonNegativeInt
    height: NonNegativeInt


# noinspection DuplicatedCode
class TMM(FileModel):
    """Terrain Material Map — uint8 material indices."""

    header: TMMHeader
    content: bytes

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header = TMMHeader.model_validate_stream(stream)
        expected_size = header.width * header.height
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
            TMMHeader.struct.pack(
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
        return stream, ".tmm"

    @property
    def bgra(self) -> bytes:
        """Palette-colored BGRA pixel data."""
        indices = np.frombuffer(self.content, dtype=np.uint8)
        return MATERIAL_PALETTE[indices].tobytes()
