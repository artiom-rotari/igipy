from io import BytesIO
from struct import Struct
from typing import ClassVar, Literal, Self

from pydantic import Field

from igipy.core.base import StructModel
from igipy.core.formats import ilff
from igipy.igi2.formats.common import REIHChunk

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


# ATTA — Attachment Points (fixed 80B records, reversed "ATTA" — same both ways)


class ATTAChunk(ilff.Chunk):
    class ATTAItem(StructModel):
        struct: ClassVar = Struct("<16s3f4f4ff4xI8x")

        name: bytes = Field(min_length=16, max_length=16)
        position_x: float
        position_y: float
        position_z: float
        orientation_x: float
        orientation_y: float
        orientation_z: float
        orientation_w: float
        secondary_x: float
        secondary_y: float
        secondary_z: float
        secondary_w: float
        unknown_float: float
        bone_index: int

    content: list[ATTAItem]

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        return {"content": cls.ATTAItem.unpack_many(content)}


# TNVE — Keyframe Data (variable-size entries, reversed "EVNT")


class TNVEPosition(StructModel):
    struct: ClassVar[Struct] = Struct("<BBH II 3f")

    entry_type: Literal[0x03]
    bone_index: int
    descriptor: int
    frame_offset: int
    reserved: int
    position_x: float
    position_y: float
    position_z: float


class TNVERotation(StructModel):
    struct: ClassVar[Struct] = Struct("<BBH II 4f4x4f4x4f4x")

    entry_type: Literal[0x04]
    bone_index: int
    descriptor: int
    frame_offset: int
    reserved: int
    quaternion_x: float
    quaternion_y: float
    quaternion_z: float
    quaternion_w: float
    in_tangent_x: float
    in_tangent_y: float
    in_tangent_z: float
    in_tangent_w: float
    out_tangent_x: float
    out_tangent_y: float
    out_tangent_z: float
    out_tangent_w: float


class TNVETrigger(StructModel):
    struct: ClassVar[Struct] = Struct("<BBH II 2I3f")

    entry_type: Literal[0x06]
    bone_index: int
    descriptor: int
    frame_offset: int
    reserved: int
    trigger_bone: int
    event_code: int
    position_x: float
    position_y: float
    position_z: float


class TNVEFullTransform(StructModel):
    struct: ClassVar[Struct] = Struct("<BBH II 3f4f4x")

    entry_type: Literal[0x07]
    bone_index: int
    descriptor: int
    frame_offset: int
    reserved: int
    position_x: float
    position_y: float
    position_z: float
    quaternion_x: float
    quaternion_y: float
    quaternion_z: float
    quaternion_w: float


class TNVEFullTransformTangent(StructModel):
    struct: ClassVar[Struct] = Struct("<BBH II I4f4f4x3ff")

    entry_type: Literal[0x01]
    bone_index: int
    descriptor: int
    frame_offset: int
    reserved: int
    unknown: int
    quaternion_a_x: float
    quaternion_a_y: float
    quaternion_a_z: float
    quaternion_a_w: float
    quaternion_b_x: float
    quaternion_b_y: float
    quaternion_b_z: float
    quaternion_b_w: float
    position_x: float
    position_y: float
    position_z: float
    scale: float


class TNVESeparator(StructModel):
    struct: ClassVar[Struct] = Struct("<BBH II")

    entry_type: Literal[0xFF]
    bone_index: int
    descriptor: int
    frame_offset: int
    reserved: int


type TNVEEntry = (
    TNVEPosition | TNVERotation | TNVETrigger | TNVEFullTransform | TNVEFullTransformTangent | TNVESeparator
)


class TNVEChunk(ilff.Chunk):
    ENTRY_MAPPING: ClassVar[dict[int, type[TNVEEntry]]] = {
        0x03: TNVEPosition,
        0x04: TNVERotation,
        0x06: TNVETrigger,
        0x07: TNVEFullTransform,
        0x01: TNVEFullTransformTangent,
        0xFF: TNVESeparator,
    }

    content: list[TNVEEntry]

    @classmethod
    def model_validate_content(cls, content: bytes) -> dict:
        stream = BytesIO(content)
        parsed_content = []

        while stream.tell() < len(content):
            entry_type = stream.read(1)[0]
            stream.seek(-1, 1)

            entry_class = cls.ENTRY_MAPPING.get(entry_type)
            if not entry_class:
                raise ValueError(f"Unknown TNVE entry type: 0x{entry_type:02X}")

            entry = entry_class.model_validate_stream(stream)
            parsed_content.append(entry)

        return {"content": parsed_content}


# IFF — ILFF container for skeletal animation


class IFF(ilff.ILFF):
    chunk_mapping: ClassVar[dict[bytes, type[ilff.Chunk]]] = {
        b"DHNA": DHNAChunk,
        b"REIH": REIHChunk,
        b"TNVE": TNVEChunk,
        b"ATTA": ATTAChunk,
    }
    field_mapping: ClassVar[dict[type[ilff.Chunk], str]] = {
        DHNAChunk: "dhna",
        REIHChunk: "reih",
        TNVEChunk: "tnve",
        ATTAChunk: "atta",
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

        field_chunks = {
            "dhna": [],
            "reih": [],
            "tnve": [],
            "atta": [],
        }

        for chunk in chunks:
            field_chunks[cls.field_mapping[type(chunk)]].append(chunk)

        instance_values: dict = {
            "header": header,
            "content_type": content_type,
        }

        if len(field_chunks["dhna"]) != 1:
            raise ValueError(f"Expected exactly 1 DHNA chunk, got {len(field_chunks['dhna'])}")

        instance_values["dhna"] = field_chunks["dhna"][0]

        if len(field_chunks["reih"]) != 1:
            raise ValueError(f"Expected exactly 1 REIH chunk, got {len(field_chunks['reih'])}")

        instance_values["reih"] = field_chunks["reih"][0]

        if len(field_chunks["tnve"]) != 1:
            raise ValueError(f"Expected exactly 1 TNVE chunk, got {len(field_chunks['tnve'])}")

        instance_values["tnve"] = field_chunks["tnve"][0]

        if len(field_chunks["atta"]) > 1:
            raise ValueError(f"Expected 0 or 1 ATTA chunks, got {len(field_chunks['atta'])}")

        if len(field_chunks["atta"]) == 0:
            instance_values["atta"] = None
        else:
            instance_values["atta"] = field_chunks["atta"][0]

        return cls(**instance_values)
