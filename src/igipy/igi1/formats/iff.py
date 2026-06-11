"""IGI 1 ``.iff`` skeletal-animation loader.

IGI 1 ``.iff`` files are EA IFF-85 (``FORM``) containers holding one shared
skeleton plus many animation clips. They are unrelated to the IGI 2 ``.iff``
format (which is an ``ILFF`` container). Chunk *sizes* are big-endian (EA IFF
convention); chunk *payloads* are little-endian (the game ran on x86).

See ``docs/igi1/formats/iff.md`` for the full format specification.

Parsing notes:
- The grouping forms ``BOBJ`` and ``BOAL`` declare a size that is 12 bytes short
  (it covers their children plus only the header of the following sibling form),
  so their sizes are ignored here. The reliable boundaries are the leaf chunks
  and the ``BOBH`` / ``BOAN`` form sizes, which tile exactly to end of file.
"""

from io import BytesIO
from struct import Struct
from typing import ClassVar, Self

from pydantic import BaseModel

from igipy.core.base import FileModel, StructModel
from igipy.core.formats.form import FORMChunkHeader

LOOPING_FLAG = 0x80000000


def _read_form_type(stream: BytesIO, expected_type: bytes) -> int:
    """Read a ``FORM`` header and its 4-byte form type; return the declared size.

    The returned size is the EA IFF chunk size (it includes the 4-byte form
    type). For the grouping forms ``BOBJ`` / ``BOAL`` this size is unreliable and
    must be ignored by the caller (see module docstring).
    """
    header = FORMChunkHeader.model_validate_stream(stream)

    if header.fourcc != b"FORM":
        raise ValueError(f"Expected FORM chunk, got {header.fourcc!r}")

    # A truncated read yields fewer than 4 bytes, which cannot equal the 4-byte
    # expected_type, so the mismatch check below also covers truncation.
    form_type = stream.read(4)

    if form_type != expected_type:
        raise ValueError(f"Expected form type {expected_type!r}, got {form_type!r}")

    return header.length


def _read_leaf(stream: BytesIO, expected_tag: bytes) -> bytes:
    """Read one leaf chunk, assert its tag, and return its content bytes.

    Odd-length chunks are word-aligned with a single trailing pad byte (EA IFF).
    """
    header = FORMChunkHeader.model_validate_stream(stream)

    if header.fourcc != expected_tag:
        raise ValueError(f"Expected {expected_tag!r} chunk, got {header.fourcc!r}")

    content = stream.read(header.length)

    if len(content) < header.length:
        raise ValueError(f"Truncated {expected_tag!r} chunk: expected {header.length} bytes, got {len(content)}")

    if header.length % 2 != 0:
        stream.read(1)

    return content


class SkeletonHeader(StructModel):
    """``BOSH`` — skeleton header."""

    struct: ClassVar[Struct] = Struct("<2i")

    object_id: int
    bone_count: int


class AnimationListHeader(StructModel):
    """``BALH`` — animation-list header."""

    struct: ClassVar[Struct] = Struct("<2i")

    animation_count: int
    animation_id_capacity: int


class ClipHeader(StructModel):
    """``BOAH`` — per-clip header."""

    struct: ClassVar[Struct] = Struct("<f2I")

    duration: float
    flags: int
    animation_id: int


class TranslationKeyframe(StructModel):
    """One ``BOTD`` record — a root-translation keyframe (40 bytes)."""

    struct: ClassVar[Struct] = Struct("<3f f 3f 3f")

    position_x: float
    position_y: float
    position_z: float
    time: float
    tangent_in_x: float
    tangent_in_y: float
    tangent_in_z: float
    tangent_out_x: float
    tangent_out_y: float
    tangent_out_z: float


class RotationKeyframe(StructModel):
    """One ``BORD`` record — a bone-rotation keyframe (52 bytes).

    ``rotation`` is the quaternion at the keyframe; ``control_b`` / ``control_c``
    are the spherical-cubic (squad) interpolation control quaternions and equal
    ``rotation`` for a constant pose.
    """

    struct: ClassVar[Struct] = Struct("<4f f 4f 4f")

    rotation_x: float
    rotation_y: float
    rotation_z: float
    rotation_w: float
    time: float
    control_b_x: float
    control_b_y: float
    control_b_z: float
    control_b_w: float
    control_c_x: float
    control_c_y: float
    control_c_z: float
    control_c_w: float


class AnimationEvent(StructModel):
    """One ``BOED`` record — a timed animation event (24 bytes)."""

    struct: ClassVar[Struct] = Struct("<I 5f")

    event_id: int
    time: float
    parameter: float
    position_x: float
    position_y: float
    position_z: float


class BoneDefinition(BaseModel):
    """A skeleton bone: parent link (``PLST``) and bind translation (``TLST``)."""

    parent_index: int
    bind_translation_x: float
    bind_translation_y: float
    bind_translation_z: float


class Animation(BaseModel):
    """One animation clip (``FORM BOAN``)."""

    duration: float
    flags: int
    animation_id: int
    looping: bool
    translation_keyframes: list[TranslationKeyframe]
    rotation_tracks: list[list[RotationKeyframe]]
    events: list[AnimationEvent]


class IFF(FileModel):
    """IGI 1 skeletal-animation library (``FORM BOBJ``)."""

    object_id: int
    bone_count: int
    bones: list[BoneDefinition]
    animations: list[Animation]

    @classmethod
    def model_validate_stream(cls, stream: BytesIO) -> Self:
        # Root: FORM BOBJ. Its declared size is unreliable (12-byte quirk) — ignore it.
        _read_form_type(stream, b"BOBJ")

        bones, bone_count, object_id = cls._read_skeleton(stream)

        # FORM BOAL follows BOBH. Its declared size is unreliable too — ignore it.
        _read_form_type(stream, b"BOAL")

        list_header = AnimationListHeader.model_validate_stream(BytesIO(_read_leaf(stream, b"BALH")))

        animations = [cls._read_animation(stream, bone_count) for _ in range(list_header.animation_count)]

        return cls(object_id=object_id, bone_count=bone_count, bones=bones, animations=animations)

    @classmethod
    def _read_skeleton(cls, stream: BytesIO) -> tuple[list[BoneDefinition], int, int]:
        # FORM BOBH: size is reliable, but we walk its leaves directly from the stream.
        _read_form_type(stream, b"BOBH")

        header = SkeletonHeader.model_validate_stream(BytesIO(_read_leaf(stream, b"BOSH")))
        bone_count = header.bone_count

        parents = _read_leaf(stream, b"PLST")
        translations = _read_leaf(stream, b"TLST")

        expected_parents = bone_count * 4
        expected_translations = bone_count * 12

        if len(parents) != expected_parents:
            raise ValueError(f"PLST length {len(parents)} != bone_count*4 ({expected_parents})")

        if len(translations) != expected_translations:
            raise ValueError(f"TLST length {len(translations)} != bone_count*12 ({expected_translations})")

        parent_values = Struct(f"<{bone_count}i").unpack(parents)
        translation_values = Struct(f"<{bone_count * 3}f").unpack(translations)

        bones = [
            BoneDefinition(
                parent_index=parent_values[index],
                bind_translation_x=translation_values[index * 3],
                bind_translation_y=translation_values[index * 3 + 1],
                bind_translation_z=translation_values[index * 3 + 2],
            )
            for index in range(bone_count)
        ]

        return bones, bone_count, header.object_id

    @classmethod
    def _read_animation(cls, stream: BytesIO, bone_count: int) -> Animation:
        # FORM BOAN: size is reliable. Read the header, then walk leaves; the clip
        # ends exactly where the next BOAN (or EOF) begins.
        size = _read_form_type(stream, b"BOAN")
        body = stream.read(size - 4)

        if len(body) < size - 4:
            raise ValueError(f"Truncated BOAN: expected {size - 4} body bytes, got {len(body)}")

        if size % 2 != 0:
            stream.read(1)

        clip_stream = BytesIO(body)

        clip_header = ClipHeader.model_validate_stream(BytesIO(_read_leaf(clip_stream, b"BOAH")))

        translation_keyframes = cls._read_track(
            clip_stream, count_tag=b"BOTH", data_tag=b"BOTD", record=TranslationKeyframe
        )

        rotation_tracks = [
            cls._read_track(clip_stream, count_tag=b"BORH", data_tag=b"BORD", record=RotationKeyframe)
            for _ in range(bone_count)
        ]

        events = cls._read_track(clip_stream, count_tag=b"BOEH", data_tag=b"BOED", record=AnimationEvent)

        return Animation(
            duration=clip_header.duration,
            flags=clip_header.flags,
            animation_id=clip_header.animation_id,
            looping=bool(clip_header.flags & LOOPING_FLAG),
            translation_keyframes=translation_keyframes,
            rotation_tracks=rotation_tracks,
            events=events,
        )

    @staticmethod
    def _read_track[RecordType: StructModel](
        stream: BytesIO, *, count_tag: bytes, data_tag: bytes, record: type[RecordType]
    ) -> list[RecordType]:
        """Read a ``<count_tag>`` keyframe count followed by its ``<data_tag>`` records."""
        count = Struct("<i").unpack(_read_leaf(stream, count_tag))[0]
        records = record.unpack_many(_read_leaf(stream, data_tag))

        if len(records) != count:
            raise ValueError(f"{data_tag!r} holds {len(records)} records but {count_tag!r} declared {count}")

        return records
