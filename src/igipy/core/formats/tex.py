from io import BytesIO
from struct import Struct, unpack
from typing import ClassVar, Literal, Self, Union

import numpy as np
from pydantic import BaseModel, NonNegativeInt

from igipy.core.base import FileModel, StructModel

TEX_VERSION_02 = 2
TEX_VERSION_07 = 7
TEX_VERSION_09 = 9
TEX_VERSION_11 = 11


class TEX(FileModel):
    variant: Union["TEX02", "TEX07", "TEX09", "TEX11"]

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        _, version = unpack("4sI", stream.read(8))

        stream.seek(0)

        if version == TEX_VERSION_02:
            variant = TEX02.model_validate_stream(stream)
        elif version == TEX_VERSION_07:
            variant = TEX07.model_validate_stream(stream)
        elif version == TEX_VERSION_09:
            variant = TEX09.model_validate_stream(stream)
        elif version == TEX_VERSION_11:
            variant = TEX11.model_validate_stream(stream)
        else:
            raise ValueError(f"Unsupported version: {version}")

        return cls(variant=variant)

    def model_dump_stream(self) -> tuple[BytesIO, str]:
        return self.variant.model_dump_stream()

    @property
    def mipmaps(self) -> list["Mipmap"]:
        if isinstance(self.variant, TEX02):
            return [self.variant.content]
        if isinstance(self.variant, (TEX07, TEX09)):
            return self.variant.item_contents
        if isinstance(self.variant, TEX11):
            return self.variant.content
        raise ValueError(f"Unsupported variant: {self.variant}")


class TEX02(BaseModel):
    header: "TEX02Header"
    content: "Mipmap"

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header = TEX02Header.model_validate_stream(stream)
        content = Mipmap.model_validate_stream(stream, width=header.width, height=header.height, mode=header.mode)

        if stream.read(1) != b"":
            raise ValueError("Parsing incomplete. Expected to reach EOF.")

        return cls(header=header, content=content)

    def model_dump_stream(self) -> tuple[BytesIO, str]:
        stream = BytesIO()
        h = self.header
        stream.write(
            TEX02Header.struct.pack(
                h.signature,
                h.version,
                h.unknown_01,
                h.unknown_02,
                h.unknown_03,
                h.unknown_04,
                h.unknown_05,
                h.width,
                h.height,
                h.mode,
            )
        )
        stream.write(self.content.bitmap)
        stream.seek(0)
        return stream, ".tex"


class TEX07(BaseModel):
    header: "TEX07Header"
    item_headers: list["TEX07ItemHeader"]
    item_contents: list["Mipmap"]
    footer: "TEX06"

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header = TEX07Header.model_validate_stream(stream)
        item_headers = [TEX07ItemHeader.model_validate_stream(stream) for _ in range(header.count)]
        item_contents = [
            Mipmap.model_validate_stream(
                stream,
                width=header.width,
                height=header.height,
                mode=header.mode,
            )
            for _ in range(header.count)
        ]
        footer = TEX06.model_validate_stream(stream)

        if stream.read(1) != b"":
            raise ValueError("Parsing incomplete. Expected to reach EOF.")

        return cls(header=header, item_headers=item_headers, item_contents=item_contents, footer=footer)

    def model_dump_stream(self) -> tuple[BytesIO, str]:
        stream = BytesIO()
        h = self.header
        stream.write(
            TEX07Header.struct.pack(
                h.signature,
                h.version,
                h.unknown_01,
                h.unknown_02,
                h.unknown_03,
                h.unknown_04,
                h.unknown_05,
                h.offset,
                h.count,
                h.unknown_06,
                h.width,
                h.height,
                h.mode,
            )
        )
        for ih in self.item_headers:
            stream.write(
                TEX07ItemHeader.struct.pack(
                    ih.offset,
                    ih.unknown_01,
                    ih.width,
                    ih.unknown_02,
                    ih.height,
                    ih.unknown_03,
                    ih.unknown_04,
                    ih.unknown_05,
                    ih.unknown_06,
                    ih.unknown_07,
                    ih.unknown_08,
                    ih.unknown_09,
                    ih.unknown_10,
                    ih.unknown_11,
                    ih.unknown_12,
                    ih.unknown_13,
                    ih.unknown_14,
                    ih.unknown_15,
                )
            )
        for mipmap in self.item_contents:
            stream.write(mipmap.bitmap)
        stream.write(self._dump_tex06(self.footer))
        stream.seek(0)
        return stream, ".tex"

    @staticmethod
    def _dump_tex06(footer: "TEX06") -> bytes:
        buffer = BytesIO()
        footer_header = footer.header
        buffer.write(
            TEX06Header.struct.pack(
                footer_header.signature,
                footer_header.version,
                footer_header.unknown_01,
                footer_header.unknown_02,
                footer_header.unknown_03,
                footer_header.unknown_04,
                footer_header.count_x,
                footer_header.count_y,
            )
        )
        for content_item in footer.content:
            buffer.write(
                TEX06Content.struct.pack(
                    content_item.unknown_01,
                    content_item.unknown_02,
                    content_item.unknown_03,
                    content_item.unknown_04,
                )
            )
        return buffer.getvalue()

    @property
    def bitmap(self) -> np.ndarray:
        tiles: list[np.ndarray] = [tile.bitmap_np for tile in self.item_contents]
        tiles_columns: int = self.footer.header.count_x
        tiles_rows: int = self.footer.header.count_y

        tile_height, tile_width = tiles[0].shape
        full_image = np.zeros((tiles_rows * tile_height, tiles_columns * tile_width), dtype=tiles[0].dtype)

        for index, tile in enumerate(tiles):
            row, col = divmod(index, tiles_columns)
            full_image[row * tile_height : (row + 1) * tile_height, col * tile_width : (col + 1) * tile_width] = tile

        return full_image


class TEX09(TEX07):
    header: "TEX09Header"
    item_headers: list["TEX09ItemHeader"]
    item_contents: list["Mipmap"]
    footer: "TEX06"

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header = TEX09Header.model_validate_stream(stream)
        item_headers = [TEX09ItemHeader.model_validate_stream(stream) for _ in range(header.count)]
        item_contents = [
            Mipmap.model_validate_stream(
                stream,
                width=header.width,
                height=header.height,
                mode=header.mode,
            )
            for _ in range(header.count)
        ]
        footer = TEX06.model_validate_stream(stream)

        if stream.read(1) != b"":
            raise ValueError("Parsing incomplete. Expected to reach EOF.")

        return cls(header=header, item_headers=item_headers, item_contents=item_contents, footer=footer)

    def model_dump_stream(self) -> tuple[BytesIO, str]:
        stream = BytesIO()
        h = self.header
        stream.write(
            TEX09Header.struct.pack(
                h.signature,
                h.version,
                h.unknown_01,
                h.unknown_02,
                h.unknown_03,
                h.unknown_04,
                h.unknown_05,
                h.offset,
                h.count,
                h.unknown_06,
                h.width,
                h.height,
                h.mode,
            )
        )
        for ih in self.item_headers:
            stream.write(
                TEX09ItemHeader.struct.pack(
                    ih.offset,
                    ih.mode,
                    ih.unknown_01,
                    ih.width,
                    ih.height,
                    ih.unknown_02,
                    ih.unknown_03,
                    ih.unknown_04,
                    ih.unknown_05,
                    ih.unknown_06,
                )
            )
        for mipmap in self.item_contents:
            stream.write(mipmap.bitmap)
        stream.write(self._dump_tex06(self.footer))
        stream.seek(0)
        return stream, ".tex"


class TEX11(BaseModel):
    header: "TEX11Header"
    content: list["Mipmap"]

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header = TEX11Header.model_validate_stream(stream)
        content = []

        for level in range(10):
            position = stream.tell()

            if stream.read(1) == b"":
                break

            stream.seek(position)

            content.append(
                Mipmap.model_validate_stream(
                    stream,
                    width=header.width,
                    height=header.height,
                    mode=header.mode,
                    level=level,
                )
            )

        if stream.read(1) != b"":
            raise ValueError("Parsing incomplete. Expected to reach EOF.")

        return cls(header=header, content=content)

    def model_dump_stream(self) -> tuple[BytesIO, str]:
        stream = BytesIO()
        h = self.header
        stream.write(
            TEX11Header.struct.pack(
                h.signature,
                h.version,
                h.mode,
                h.unknown_01,
                h.unknown_02,
                h.unknown_03,
                h.width,
                h.height,
                h.width_02,
                h.height_02,
                h.pixel_depth,
            )
        )
        for mipmap in self.content:
            stream.write(mipmap.bitmap)
        stream.seek(0)
        return stream, ".tex"


class TEX06(BaseModel):
    header: "TEX06Header"
    content: list["TEX06Content"]

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header = TEX06Header.model_validate_stream(stream)
        content = [TEX06Content.model_validate_stream(stream) for _ in range(header.count_x * header.count_y)]
        return cls(header=header, content=content)


class TEX02Header(StructModel):
    struct: ClassVar[Struct] = Struct("4sI8H")

    signature: Literal[b"LOOP"]
    version: Literal[2]
    unknown_01: Literal[0]
    unknown_02: Literal[0]
    unknown_03: Literal[0]
    unknown_04: Literal[0]
    unknown_05: NonNegativeInt  # always 128
    width: NonNegativeInt  # always 64
    height: NonNegativeInt  # always 64
    mode: Literal[2, 3, 67]  # always 2


class TEX07Header(StructModel):
    struct: ClassVar[Struct] = Struct("4s12I")

    signature: Literal[b"LOOP"]
    version: Literal[7]
    unknown_01: Literal[2880154539]
    unknown_02: Literal[2880154539]
    unknown_03: Literal[0]
    unknown_04: Literal[0]
    unknown_05: Literal[0]
    offset: NonNegativeInt
    count: NonNegativeInt
    unknown_06: Literal[2880154539]
    width: NonNegativeInt
    height: NonNegativeInt
    mode: Literal[2, 3, 67]  # always 3


class TEX09Header(TEX07Header):
    version: Literal[9]
    unknown_01: Literal[0]
    unknown_02: Literal[0]
    unknown_03: Literal[327680]
    unknown_06: Literal[0]
    mode: Literal[2, 3, 67]  # always 2 or 3


class TEX11Header(StructModel):
    struct: ClassVar[Struct] = Struct("4s4I6H")

    signature: Literal[b"LOOP"]
    version: Literal[11]
    mode: Literal[2, 3, 67]
    unknown_01: Literal[0, 524288]
    unknown_02: Literal[0]
    unknown_03: Literal[2, 3, 4, 5, 6, 7, 8]
    width: NonNegativeInt
    height: NonNegativeInt
    width_02: NonNegativeInt
    height_02: NonNegativeInt
    pixel_depth: Literal[2, 4]


class Mipmap(BaseModel):
    class Header(BaseModel):
        level: NonNegativeInt
        mode: NonNegativeInt
        width: NonNegativeInt
        height: NonNegativeInt

        @property
        def bitmap_width(self) -> int:
            return self.width // (1 << self.level)

        @property
        def bitmap_height(self) -> int:
            return self.height // (1 << self.level)

        @property
        def bitmap_depth(self) -> int:
            return {2: 2, 3: 4, 67: 4}[self.mode]

    header: Header
    bitmap: bytes

    @classmethod
    def model_validate_stream(cls, stream: BytesIO, width: int, height: int, mode: int, level: int = 0) -> Self:
        header = cls.Header(level=level, mode=mode, width=width, height=height)
        bitmap = stream.read(header.bitmap_width * header.bitmap_height * header.bitmap_depth)
        return cls(header=header, bitmap=bitmap)

    @property
    def bitmap_np(self) -> np.ndarray:
        bitmap_np = np.frombuffer(self.bitmap, dtype={2: np.uint16, 3: np.uint32, 67: np.uint32}[self.header.mode])
        return bitmap_np.reshape((self.header.height, self.header.width))


class TEX06Header(StructModel):
    struct: ClassVar[Struct] = Struct("4sI4H2I")

    signature: Literal[b"LOOP"]
    version: Literal[6]
    unknown_01: NonNegativeInt
    unknown_02: NonNegativeInt
    unknown_03: NonNegativeInt
    unknown_04: NonNegativeInt
    count_x: NonNegativeInt
    count_y: NonNegativeInt


class TEX06Content(StructModel):
    struct: ClassVar[Struct] = Struct("4I")

    unknown_01: NonNegativeInt
    unknown_02: NonNegativeInt
    unknown_03: NonNegativeInt
    unknown_04: NonNegativeInt


class TEX07ItemHeader(StructModel):
    struct: ClassVar[Struct] = Struct("2I16H")

    offset: NonNegativeInt
    unknown_01: NonNegativeInt
    width: NonNegativeInt
    unknown_02: NonNegativeInt
    height: NonNegativeInt
    unknown_03: NonNegativeInt
    unknown_04: NonNegativeInt
    unknown_05: NonNegativeInt
    unknown_06: NonNegativeInt
    unknown_07: NonNegativeInt
    unknown_08: NonNegativeInt
    unknown_09: NonNegativeInt
    unknown_10: NonNegativeInt
    unknown_11: NonNegativeInt
    unknown_12: NonNegativeInt
    unknown_13: NonNegativeInt
    unknown_14: NonNegativeInt
    unknown_15: NonNegativeInt


class TEX09ItemHeader(StructModel):
    struct: ClassVar[Struct] = Struct("2I4H4I")

    offset: NonNegativeInt
    mode: NonNegativeInt
    unknown_01: NonNegativeInt
    width: NonNegativeInt
    height: NonNegativeInt
    unknown_02: NonNegativeInt
    unknown_03: NonNegativeInt
    unknown_04: NonNegativeInt
    unknown_05: NonNegativeInt
    unknown_06: NonNegativeInt
