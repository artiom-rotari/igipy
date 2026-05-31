import struct
from io import BytesIO
from struct import Struct
from typing import ClassVar, Self

from pydantic import NonNegativeInt

from igipy.core.base import FileModel, StructModel

HEADER_SIZE = 14
HEADER_VALUE = 10
VERSION_STRING = b"Ver. 3.0"


class ForestRecord(StructModel):
    struct: ClassVar[Struct] = Struct("<9f4B")

    position_x: float
    position_y: float
    position_z: float
    rotation_x: float
    rotation_y: float
    rotation_z: float
    scale_x: float
    scale_y: float
    scale_z: float
    color_r: NonNegativeInt
    color_g: NonNegativeInt
    color_b: NonNegativeInt
    color_a: NonNegativeInt


class DATForest(FileModel):
    """DAT Forest — vegetation instance placement data."""

    header_value: NonNegativeInt
    version: str
    records: list[ForestRecord]

    def model_dump_stream(self) -> tuple[BytesIO, str]:
        stream = BytesIO()
        stream.write(struct.pack("<I", self.header_value))
        stream.write(b"\x0a")
        stream.write(self.version.encode("ascii"))
        stream.write(b"\x0a")
        for record in self.records:
            stream.write(
                ForestRecord.struct.pack(
                    record.position_x,
                    record.position_y,
                    record.position_z,
                    record.rotation_x,
                    record.rotation_y,
                    record.rotation_z,
                    record.scale_x,
                    record.scale_y,
                    record.scale_z,
                    record.color_r,
                    record.color_g,
                    record.color_b,
                    record.color_a,
                )
            )
        stream.seek(0)
        return stream, ".dat"

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        data = stream.read()

        header_value = struct.unpack_from("<I", data, 0)[0]
        if header_value != HEADER_VALUE:
            raise ValueError(f"Expected header value {HEADER_VALUE}, got {header_value}")

        if data[4:5] != b"\x0a":
            raise ValueError("Expected newline after header value")

        version = data[5:13]
        if version != VERSION_STRING:
            raise ValueError(f"Expected version '{VERSION_STRING!r}', got {version!r}")

        if data[13:14] != b"\x0a":
            raise ValueError("Expected newline after version string")

        record_data = data[HEADER_SIZE:]
        length, remainder = divmod(len(record_data), ForestRecord.struct.size)

        if remainder != 0:
            raise ValueError(
                f"Record data length {len(record_data)} is not divisible by record size {ForestRecord.struct.size}"
            )

        record_stream = BytesIO(record_data)
        records = [ForestRecord.model_validate_stream(record_stream) for _ in range(length)]

        return cls(header_value=header_value, version=version.decode("ascii"), records=records)
