from io import BytesIO
from struct import Struct
from typing import ClassVar, Self

from pydantic import BaseModel


class FileModel(BaseModel):
    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        """Method to parse the file from a binary stream"""
        raise NotImplementedError

    def model_dump_stream(self) -> tuple[BytesIO, str]:
        """Method to dump the file to a binary stream"""
        raise NotImplementedError


class FileIgnored(NotImplementedError):  # noqa: N818
    """Raise when this file is ignored intentionally"""


class StructModel(BaseModel):
    struct: ClassVar[Struct]

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        cls_fields = cls.__pydantic_fields__.keys()
        cls_values = cls.struct.unpack(stream.read(cls.struct.size))
        # noinspection PyArgumentList
        return cls(**dict(zip(cls_fields, cls_values, strict=True)))

    @classmethod
    def unpack_many(cls, data: bytes) -> list[Self]:
        length, remainder = divmod(len(data), cls.struct.size)

        if remainder != 0:
            raise ValueError(f"Data length {len(data)} is not divisible by struct size {cls.struct.size}")

        stream = BytesIO(data)
        return [cls.model_validate_stream(stream) for _ in range(length)]
