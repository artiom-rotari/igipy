from io import BytesIO
from struct import Struct
from typing import ClassVar, Self

import numpy as np
from pydantic import BaseModel, NonNegativeInt

from igipy.core.base import FileModel, StructModel


class OLMHeader(StructModel):
    """OLM main header — 88 bytes."""

    struct: ClassVar[Struct] = Struct("<2f7I3I4I4H I3f")

    version1: float
    version2: float
    year: NonNegativeInt
    month: NonNegativeInt
    day: NonNegativeInt
    hour: NonNegativeInt
    minute: NonNegativeInt
    second: NonNegativeInt
    millisecond: NonNegativeInt
    unknown_0: NonNegativeInt
    count1: NonNegativeInt
    layer_count: NonNegativeInt
    reserved_0: NonNegativeInt
    reserved_1: NonNegativeInt
    reserved_2: NonNegativeInt
    reserved_3: NonNegativeInt
    width: NonNegativeInt
    height: NonNegativeInt
    total_stride: NonNegativeInt
    format: NonNegativeInt
    pad: NonNegativeInt
    uv_scale_u: float
    uv_scale_v: float
    zero: float


class OLMLayerHeader(StructModel):
    """Per-layer descriptor — 24 bytes."""

    struct: ClassVar[Struct] = Struct("<5I2H")

    flags: NonNegativeInt
    ptr1: NonNegativeInt
    ptr2: NonNegativeInt
    val: NonNegativeInt
    pad: NonNegativeInt
    pixel_width: NonNegativeInt
    pixel_height: NonNegativeInt


class OLMLayerExtra(StructModel):
    """Extra block between layer descriptors — 28 bytes."""

    struct: ClassVar[Struct] = Struct("<I2H2HI2fI")

    pad_0: NonNegativeInt
    block_width: NonNegativeInt
    block_height: NonNegativeInt
    block_stride: NonNegativeInt
    block_format: NonNegativeInt
    pad_1: NonNegativeInt
    block_uv_u: float
    block_uv_v: float
    pad_2: NonNegativeInt


class OLMLayer(BaseModel):
    header: OLMLayerHeader
    extra: OLMLayerExtra | None = None
    content: bytes

    @property
    def bgra(self) -> bytes:
        """BGRA pixel data (swapped from stored RGBA)."""
        rgba = np.frombuffer(self.content, dtype=np.uint8).reshape(-1, 4)
        return rgba[:, [2, 1, 0, 3]].tobytes()


class OLM(FileModel):
    """Object Lightmap — per-object RGBA lightmap with one or more layers."""

    header: OLMHeader
    layers: list[OLMLayer]

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header = OLMHeader.model_validate_stream(stream)

        layer_headers: list[OLMLayerHeader] = []
        layer_extras: list[OLMLayerExtra | None] = []

        for i in range(header.layer_count):
            layer_header = OLMLayerHeader.model_validate_stream(stream)
            layer_headers.append(layer_header)

            if i < header.layer_count - 1:
                layer_extras.append(OLMLayerExtra.model_validate_stream(stream))
            else:
                layer_extras.append(None)

        layers = []
        for i in range(header.layer_count):
            expected_size = layer_headers[i].pixel_width * layer_headers[i].pixel_height * 4
            content = stream.read(expected_size)

            if len(content) != expected_size:
                raise ValueError(f"Layer {i}: expected {expected_size} bytes, got {len(content)}")

            layers.append(OLMLayer(header=layer_headers[i], extra=layer_extras[i], content=content))

        if stream.read(1) != b"":
            raise ValueError("Expected end of stream")

        return cls(header=header, layers=layers)
