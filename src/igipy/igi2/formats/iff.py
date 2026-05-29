from collections import defaultdict
from io import BytesIO
from struct import Struct
from typing import ClassVar, Self, Union

from pydantic import BaseModel, Field

from igipy.core.base import StructModel
from igipy.core.formats import ilff

# DHNA — Animation Header (variable size, reversed "ANHD")


class DHNAChunk(ilff.Chunk):
    version: int
    looping: int
    duration: int
    bone_count: int
    entry_count: int
    unknown_01: int
    has_root_motion: int
    unknown_02: int
    name: str

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        # Fixed fields at known offsets (skipping 0xAB padding regions)
        fields = Struct("<8x I I I I 4x I I I I 8x").unpack(content[:52])
        version, looping, duration, bone_count, entry_count, unknown_01, has_root_motion, unknown_02 = fields

        # Null-terminated ASCII name starting at offset 52
        name_bytes = content[52:]
        null_idx = name_bytes.find(b"\x00")
        name = name_bytes[:null_idx].decode("ascii") if null_idx >= 0 else name_bytes.decode("ascii")

        return {
            "version": version,
            "looping": looping,
            "duration": duration,
            "bone_count": bone_count,
            "entry_count": entry_count,
            "unknown_01": unknown_01,
            "has_root_motion": has_root_motion,
            "unknown_02": unknown_02,
            "name": name,
        }


# REIH — Bone Hierarchy (variable size, reversed "HIER")


class REIHChunk(ilff.Chunk):
    bone_type_flags: list[int]
    rest_pose_offsets: list[tuple[float, float, float]]

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        # Derive bone_count from content length: (length - 1) // 13
        bone_count = (len(content) - 1) // 13

        # First bone_count bytes are type flags
        bone_type_flags = list(content[:bone_count])

        # Skip 1 padding byte, then bone_count x 3 floats for rest-pose offsets
        offset_data = content[bone_count + 1 :]
        floats = Struct(f"<{bone_count * 3}f").unpack(offset_data)
        rest_pose_offsets = [(floats[i * 3], floats[i * 3 + 1], floats[i * 3 + 2]) for i in range(bone_count)]

        return {
            "bone_type_flags": bone_type_flags,
            "rest_pose_offsets": rest_pose_offsets,
        }


# ATTA — Attachment Points (fixed 80B records, reversed "ATTA" — same both ways)


class ATTAChunk(ilff.Chunk):
    class ATTAItem(StructModel):
        struct: ClassVar = Struct("<16s3f4f4f4xII8x")

        name: bytes = Field(min_length=16, max_length=16)
        pos_x: float
        pos_y: float
        pos_z: float
        orient_x: float
        orient_y: float
        orient_z: float
        orient_w: float
        secondary_x: float
        secondary_y: float
        secondary_z: float
        secondary_w: float
        bone_index: int
        attachment_index: int

    content: list[ATTAItem]

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.ATTAItem.unpack_many(content)}


# TNVE — Keyframe Data (variable-size entries, reversed "EVNT")


class TNVEPosition(BaseModel):
    """Type 0x03 — Position keyframe (24B)"""

    entry_type: int
    bone_index: int
    frame_offset: int
    reserved: int
    pos_x: float
    pos_y: float
    pos_z: float


class TNVERotation(BaseModel):
    """Type 0x04 — Rotation with Hermite tangents (72B)"""

    entry_type: int
    bone_index: int
    frame_offset: int
    reserved: int
    quat_x: float
    quat_y: float
    quat_z: float
    quat_w: float
    in_tangent_x: float
    in_tangent_y: float
    in_tangent_z: float
    in_tangent_w: float
    out_tangent_x: float
    out_tangent_y: float
    out_tangent_z: float
    out_tangent_w: float


class TNVEPositionInterp(BaseModel):
    """Type 0x06 — Position with interpolation data (32B)"""

    entry_type: int
    bone_index: int
    frame_offset: int
    reserved: int
    extra_a: int
    extra_b: int
    pos_x: float
    pos_y: float
    pos_z: float


class TNVEFullTransform(BaseModel):
    """Type 0x07 — Full transform: pos + rot (44B, 47-bone only)"""

    entry_type: int
    bone_index: int
    frame_offset: int
    reserved: int
    pos_x: float
    pos_y: float
    pos_z: float
    quat_x: float
    quat_y: float
    quat_z: float
    quat_w: float


class TNVEFullTransformTangent(BaseModel):
    """Type 0x01 — Full transform with tangents (68B, 47-bone only)"""

    entry_type: int
    bone_index: int
    frame_offset: int
    reserved: int
    unknown: int
    quat_a_x: float
    quat_a_y: float
    quat_a_z: float
    quat_a_w: float
    quat_b_x: float
    quat_b_y: float
    quat_b_z: float
    quat_b_w: float
    pos_x: float
    pos_y: float
    pos_z: float
    scale: float


class TNVESeparator(BaseModel):
    """Type 0xFF — Loop boundary separator (12B)"""

    entry_type: int
    bone_index: int
    frame_offset: int
    reserved: int


TNVEEntry = Union[  # noqa: UP007
    TNVEPosition, TNVERotation, TNVEPositionInterp, TNVEFullTransform, TNVEFullTransformTangent, TNVESeparator
]

_TNVE_HEADER = Struct("<BBH II")

_TNVE_PARSERS: dict[int, tuple[Struct, type[TNVEEntry]]] = {
    0x03: (Struct("<3f"), TNVEPosition),
    0x04: (Struct("<4f4x4f4x4f4x"), TNVERotation),
    0x06: (Struct("<2I3f"), TNVEPositionInterp),
    0x07: (Struct("<3f4f4x"), TNVEFullTransform),
    0x01: (Struct("<I4f4f4x3ff"), TNVEFullTransformTangent),
    0xFF: (None, TNVESeparator),
}


def _parse_tnve_entries(content: bytes) -> list[TNVEEntry]:
    stream = BytesIO(content)
    entries = []

    while stream.tell() < len(content):
        header_data = stream.read(_TNVE_HEADER.size)
        if len(header_data) < _TNVE_HEADER.size:
            break

        entry_type, bone_index, descriptor, frame_offset, reserved = _TNVE_HEADER.unpack(header_data)
        entry_size = descriptor * 4
        payload_size = entry_size - _TNVE_HEADER.size

        payload = stream.read(payload_size) if payload_size > 0 else b""

        parser_info = _TNVE_PARSERS.get(entry_type)
        if parser_info is None:
            raise ValueError(f"Unknown TNVE entry type: 0x{entry_type:02X}")

        payload_struct, entry_cls = parser_info
        common = {
            "entry_type": entry_type,
            "bone_index": bone_index,
            "frame_offset": frame_offset,
            "reserved": reserved,
        }

        if payload_struct is not None:
            values = payload_struct.unpack(payload)
            field_names = [f for f in entry_cls.model_fields if f not in common]
            common.update(zip(field_names, values, strict=True))

        entries.append(entry_cls(**common))

    return entries


class TNVEChunk(ilff.Chunk):
    content: list[TNVEEntry]

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": _parse_tnve_entries(content)}


# IFF — ILFF container for skeletal animation


class IFF(ilff.ILFF):
    chunk_mapping: ClassVar[dict[bytes, type[ilff.Chunk]]] = {
        b"DHNA": DHNAChunk,
        b"REIH": REIHChunk,
        b"TNVE": TNVEChunk,
        b"ATTA": ATTAChunk,
    }

    header: ilff.ILFFHeader
    content_type: bytes

    dhna: DHNAChunk
    reih: REIHChunk
    tnve: TNVEChunk
    atta: ATTAChunk | None = None

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        header, content_type, chunks = cls.model_validate_chunks(stream)

        if content_type != b"MINA":
            raise ValueError(f"Expected content type MINA (ANIM reversed), got {content_type}")

        field_mapping: dict[type[ilff.Chunk], str] = {
            DHNAChunk: "dhna",
            REIHChunk: "reih",
            TNVEChunk: "tnve",
            ATTAChunk: "atta",
        }

        values: dict[str, list[ilff.Chunk]] = defaultdict(list)
        for chunk in chunks:
            values[field_mapping[type(chunk)]].append(chunk)

        instance_values: dict = {"header": header, "content_type": content_type}

        for field in ["dhna", "reih", "tnve"]:
            if len(values[field]) != 1:
                raise ValueError(f"Expected exactly 1 {field.upper()} chunk, got {len(values[field])}")
            instance_values[field] = values[field][0]

        if len(values["atta"]) == 1:
            instance_values["atta"] = values["atta"][0]
        elif len(values["atta"]) > 1:
            raise ValueError(f"Expected 0 or 1 ATTA chunks, got {len(values['atta'])}")

        return cls(**instance_values)
