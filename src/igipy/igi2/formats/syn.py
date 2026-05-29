import json
import struct
from io import BytesIO
from typing import Self

from igipy.core.base import FileModel


class SYN(FileModel):
    """SYN lip-sync envelope — flat array of float32 amplitude values."""

    samples: list[float]

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        data = stream.read()
        length, remainder = divmod(len(data), 4)

        if remainder != 0:
            raise ValueError(f"SYN file size {len(data)} is not divisible by 4")

        samples = list(struct.unpack(f"<{length}f", data))
        return cls(samples=samples)

    def model_dump_stream(self) -> tuple[BytesIO, str]:
        rounded = [round(s, 4) for s in self.samples]
        content = json.dumps(rounded, indent=2).encode("utf-8")
        return BytesIO(content), ".json"
