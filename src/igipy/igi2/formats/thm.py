from io import BytesIO
from struct import Struct
from typing import ClassVar, Literal, Self

import numpy as np
from pydantic import NonNegativeInt

from igipy.core.base import FileModel, StructModel


class THMHeader(StructModel):
    """THM header — 52 bytes total (32 common + 20 extra)."""

    struct: ClassVar[Struct] = Struct("<f7IIIf2I")

    terrain_scale: float
    year: NonNegativeInt
    month: NonNegativeInt
    day: NonNegativeInt
    hour: NonNegativeInt
    minute: NonNegativeInt
    second: NonNegativeInt
    unknown: NonNegativeInt
    type: Literal[2]
    padding: Literal[0]
    height_scale: float
    width: NonNegativeInt
    height: NonNegativeInt


class THM(FileModel):
    """Terrain Height Map — float32 heightmap."""

    header: THMHeader
    content: bytes
    mipmaps: bytes = b""

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header = THMHeader.model_validate_stream(stream)
        top_level_size = header.width * header.height * 4
        content = stream.read(top_level_size)

        if len(content) != top_level_size:
            raise ValueError(f"Expected {top_level_size} bytes, got {len(content)}")

        mipmaps = stream.read()

        return cls(header=header, content=content, mipmaps=mipmaps)

    def model_dump_stream(self) -> tuple[BytesIO, str]:
        stream = BytesIO()
        h = self.header
        stream.write(
            THMHeader.struct.pack(
                h.terrain_scale,
                h.year,
                h.month,
                h.day,
                h.hour,
                h.minute,
                h.second,
                h.unknown,
                h.type,
                h.padding,
                h.height_scale,
                h.width,
                h.height,
            )
        )
        stream.write(self.content)
        stream.write(self.mipmaps)
        stream.seek(0)
        return stream, ".thm"

    @property
    def bgra(self) -> bytes:
        """Normalized grayscale BGRA pixel data."""
        heights = np.frombuffer(self.content, dtype="<f4")

        min_h, max_h = heights.min(), heights.max()
        span = max_h - min_h

        if span > 0:
            normalized = ((heights - min_h) / span * 255).astype(np.uint8)
        else:
            normalized = np.zeros(len(heights), dtype=np.uint8)

        bgra = np.empty((len(heights), 4), dtype=np.uint8)
        bgra[:, 0] = normalized
        bgra[:, 1] = normalized
        bgra[:, 2] = normalized
        bgra[:, 3] = 255

        return bgra.tobytes()
