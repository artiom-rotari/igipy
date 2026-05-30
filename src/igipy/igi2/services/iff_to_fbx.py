"""Export IFF skeletal animation to FBX 7.5 ASCII format.

Produces a skeleton-only animation (no mesh geometry). The result can be
imported into Blender, Maya, 3ds Max, or any FBX-compatible DCC tool.
Bones are represented as LimbNode models; animation channels carry
translation and rotation keyframes extracted from TNVE entries.
"""

import math
from collections import defaultdict
from io import BytesIO
from pathlib import Path

from igipy.core.formats.fbx import (
    FBX,
    FBX_TIME_ONE_SECOND,
    FBXAnimationCurve,
    FBXAnimationCurveNode,
    FBXAnimationLayer,
    FBXAnimationStack,
    FBXConnection,
    FBXModel,
    FBXNodeAttribute,
    IdGenerator,
)
from igipy.igi2.formats.iff import (
    IFF,
    TNVEFullTransform,
    TNVEFullTransformTangent,
    TNVEPosition,
    TNVERotation,
    TNVESeparator,
    TNVETrigger,
)

# IGI2 uses fixed-point precision: 4096 units (2^12) = 1 meter.
SCALE = 1 / 4096

QUATERNION_EPSILON = 1e-10

# bone_index = 0xABABABAB is the MSVC debug heap fill sentinel meaning "no bone"
ATTA_NO_BONE = 0xABABABAB

# Bone names from MEF MANB chunk for the 31-bone human skeleton.
_BONE_NAMES_31 = [
    "center",
    "lower body",
    "upper left leg",
    "upper right leg",
    "upper body",
    "lower left leg",
    "lower right leg",
    "shoulders",
    "left foot",
    "right foot",
    "rotate_head",
    "rotate_left",
    "rotate_right",
    "left toe",
    "right toe",
    "head",
    "upper left arm",
    "upper right arm",
    "left toe end",
    "right toe end",
    "head end",
    "lower left arm",
    "lower right arm",
    "left hand",
    "right hand",
    "upper left finger",
    "upper right finger",
    "lower left finger",
    "lower right finger",
    "left fingers end",
    "right fingers end",
]

# Bone names from MEF MANB chunk for the 47-bone first-person hand skeleton.
_BONE_NAMES_47 = [
    "center shoulders",
    "upper left arm",
    "upper right arm",
    "lower left arm",
    "lower right arm",
    "left hand",
    "right hand",
    "upper left foref",
    "upper left littl",
    "upper left middl",
    "upper left ring",
    "upper left thumb",
    "upper right fore",
    "upper right litt",
    "upper right midd",
    "upper right ring",
    "upper right thum",
    "lower left foref",
    "lower left littl",
    "lower left middl",
    "lower left ring",
    "lower left thumb",
    "lower right fore",
    "lower right litt",
    "lower right midd",
    "lower right ring",
    "lower right thum",
    "left forefinger",
    "left little fing",
    "left middle fing",
    "left ring finger",
    "left thumb tip",
    "right forefinger",
    "right little fin",
    "right middle fin",
    "right ring finge",
    "right thumb tip",
    "none09",
    "none07",
    "none06",
    "none08",
    "none10",
    "none02",
    "none05",
    "none03",
    "none04",
    "none01",
]

_BONE_NAME_MAP: dict[int, list[str]] = {
    len(_BONE_NAMES_31): _BONE_NAMES_31,
    len(_BONE_NAMES_47): _BONE_NAMES_47,
}


def _position_to_fbx(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Convert position from IGI2 Z-up to FBX Y-up coordinates."""
    return round(x * SCALE, 4), round(z * SCALE, 4), round(-y * SCALE, 4)


def _normalize_quaternion(x: float, y: float, z: float, w: float) -> tuple[float, float, float, float]:
    length = math.sqrt(x * x + y * y + z * z + w * w)
    if length < QUATERNION_EPSILON:
        return 0.0, 0.0, 0.0, 1.0
    inverse_length = 1.0 / length
    return x * inverse_length, y * inverse_length, z * inverse_length, w * inverse_length


def _quaternion_to_fbx(x: float, y: float, z: float, w: float) -> tuple[float, float, float, float]:
    """Convert quaternion from IGI2 Z-up to FBX Y-up coordinates."""
    return _normalize_quaternion(x, z, -y, w)


def _quaternion_to_euler(qx: float, qy: float, qz: float, qw: float) -> tuple[float, float, float]:
    """Convert quaternion to Euler angles (degrees) in XYZ order."""
    sinr_cosp = 2.0 * (qw * qx + qy * qz)
    cosr_cosp = 1.0 - 2.0 * (qx * qx + qy * qy)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    sinp = 2.0 * (qw * qy - qz * qx)
    pitch = math.copysign(math.pi / 2.0, sinp) if abs(sinp) >= 1.0 else math.asin(sinp)

    siny_cosp = 2.0 * (qw * qz + qx * qy)
    cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return round(math.degrees(roll), 4), round(math.degrees(pitch), 4), round(math.degrees(yaw), 4)


def _collect_tracks(
    iff: IFF,
) -> tuple[
    dict[int, list[tuple[float, tuple[float, float, float]]]],
    dict[int, list[tuple[float, tuple[float, float, float]]]],
]:
    """Group TNVE entries into per-bone translation and rotation tracks.

    Returns (translation_tracks, rotation_tracks) where each maps
    bone_index -> sorted list of (time_normalized, values).
    Rotation values are Euler angles (degrees) for FBX.
    """
    duration = max(iff.dhna.duration, 1)

    translation_tracks: dict[int, list[tuple[float, tuple[float, float, float]]]] = defaultdict(list)
    rotation_tracks: dict[int, list[tuple[float, tuple[float, float, float]]]] = defaultdict(list)

    for entry in iff.tnve.content:
        if isinstance(entry, TNVESeparator):
            break

        normalized_time = entry.frame_offset / duration

        if isinstance(entry, TNVEPosition):
            position = _position_to_fbx(entry.position_x, entry.position_y, entry.position_z)
            translation_tracks[entry.bone_index].append((normalized_time, position))
        elif isinstance(entry, TNVETrigger):
            pass
        elif isinstance(entry, TNVERotation):
            qx, qy, qz, qw = _quaternion_to_fbx(
                entry.quaternion_x,
                entry.quaternion_y,
                entry.quaternion_z,
                entry.quaternion_w,
            )
            rotation_tracks[entry.bone_index].append((normalized_time, _quaternion_to_euler(qx, qy, qz, qw)))
        elif isinstance(entry, TNVEFullTransform):
            position = _position_to_fbx(entry.position_x, entry.position_y, entry.position_z)
            translation_tracks[entry.bone_index].append((normalized_time, position))
            qx, qy, qz, qw = _quaternion_to_fbx(
                entry.quaternion_x,
                entry.quaternion_y,
                entry.quaternion_z,
                entry.quaternion_w,
            )
            rotation_tracks[entry.bone_index].append((normalized_time, _quaternion_to_euler(qx, qy, qz, qw)))
        elif isinstance(entry, TNVEFullTransformTangent):
            position = _position_to_fbx(entry.position_x, entry.position_y, entry.position_z)
            translation_tracks[entry.bone_index].append((normalized_time, position))
            qx, qy, qz, qw = _quaternion_to_fbx(
                entry.quaternion_a_x,
                entry.quaternion_a_y,
                entry.quaternion_a_z,
                entry.quaternion_a_w,
            )
            rotation_tracks[entry.bone_index].append((normalized_time, _quaternion_to_euler(qx, qy, qz, qw)))

    for track in translation_tracks.values():
        track.sort(key=lambda keyframe: keyframe[0])
    for track in rotation_tracks.values():
        track.sort(key=lambda keyframe: keyframe[0])

    return translation_tracks, rotation_tracks


def _get_bone_name(bone_index: int, bone_count: int) -> str:
    names = _BONE_NAME_MAP.get(bone_count)
    if names and bone_index < len(names):
        return names[bone_index]
    return f"bone_{bone_index:03d}"


def iff_to_fbx(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:  # noqa: C901, PLR0912, PLR0915
    target_path: Path | None = source_path.with_suffix(".fbx") if source_path is not None else None
    iff = IFF.model_validate_stream(source_io)

    bone_count = iff.dhna.bone_count
    parent_map = iff.reih.bones_parents
    rest_pose_offsets = iff.reih.bones_offsets
    translation_tracks, rotation_tracks = _collect_tracks(iff)

    id_gen = IdGenerator()

    # Node attributes and models for bones
    bone_node_attribute_ids = [id_gen() for _ in range(bone_count)]
    bone_ids = [id_gen() for _ in range(bone_count)]

    node_attributes: list[FBXNodeAttribute] = []
    models: list[FBXModel] = []

    for i in range(bone_count):
        name = _get_bone_name(i, bone_count)
        node_attributes.append(
            FBXNodeAttribute(id=bone_node_attribute_ids[i], name=name, type="LimbNode", type_flags="Skeleton"),
        )
        translation = _position_to_fbx(*rest_pose_offsets[i]) if i < len(rest_pose_offsets) else (0.0, 0.0, 0.0)
        models.append(
            FBXModel(
                id=bone_ids[i],
                name=name,
                type="LimbNode",
                translation=translation,
                default_attribute_index=0,
                shading=True,
                culling=True,
            )
        )

    # Attachments
    attachment_count = len(iff.atta.content) if iff.atta else 0
    attachment_node_attribute_ids = [id_gen() for _ in range(attachment_count)]
    attachment_ids = [id_gen() for _ in range(attachment_count)]

    if iff.atta:
        for i, item in enumerate(iff.atta.content):
            name = "attach_" + item.name.rstrip(b"\x00").decode("ascii", errors="replace")
            node_attributes.append(
                FBXNodeAttribute(id=attachment_node_attribute_ids[i], name=name, type="Null", type_flags="Null"),
            )
            translation_x, translation_y, translation_z = _position_to_fbx(
                item.position_x, item.position_y, item.position_z
            )
            quaternion_x, quaternion_y, quaternion_z, quaternion_w = _quaternion_to_fbx(
                item.orientation_x,
                item.orientation_y,
                item.orientation_z,
                item.orientation_w,
            )
            rotation_x, rotation_y, rotation_z = _quaternion_to_euler(
                quaternion_x, quaternion_y, quaternion_z, quaternion_w
            )
            models.append(
                FBXModel(
                    id=attachment_ids[i],
                    name=name,
                    type="Null",
                    translation=(translation_x, translation_y, translation_z),
                    rotation=(rotation_x, rotation_y, rotation_z),
                    default_attribute_index=0,
                    shading=True,
                    culling=True,
                )
            )

    # Animation
    animation_stacks: list[FBXAnimationStack] = []
    animation_layers: list[FBXAnimationLayer] = []
    animation_curve_nodes: list[FBXAnimationCurveNode] = []
    animation_curves: list[FBXAnimationCurve] = []
    animation_connections: list[FBXConnection] = []

    animation_stack_id = id_gen()
    animation_layer_id = id_gen()

    has_animation = bool(translation_tracks or rotation_tracks)

    if has_animation:
        animation_stacks.append(FBXAnimationStack(id=animation_stack_id, name=iff.dhna.name))
        animation_layers.append(FBXAnimationLayer(id=animation_layer_id))
        animation_connections.append(FBXConnection(source=animation_layer_id, destination=animation_stack_id))

        for bone_index in sorted(translation_tracks):
            if bone_index >= bone_count:
                continue
            track = translation_tracks[bone_index]
            if not track:
                continue
            curve_node_id = id_gen()
            times = [kf[0] for kf in track]
            animation_curve_nodes.append(FBXAnimationCurveNode(id=curve_node_id, channel="T"))
            animation_connections.append(FBXConnection(source=curve_node_id, destination=animation_layer_id))
            animation_connections.append(
                FBXConnection(
                    src=curve_node_id,
                    dst=bone_ids[bone_index],
                    property="Lcl Translation",
                )
            )
            for axis, label in enumerate(("X", "Y", "Z")):
                curve_id = id_gen()
                animation_curves.append(
                    FBXAnimationCurve(
                        id=curve_id,
                        key_time=[int(t * FBX_TIME_ONE_SECOND) for t in times],
                        key_value_float=[kf[1][axis] for kf in track],
                    )
                )
                animation_connections.append(
                    FBXConnection(source=curve_id, destination=curve_node_id, property=f"d|{label}")
                )

        for bone_index in sorted(rotation_tracks):
            if bone_index >= bone_count:
                continue
            track = rotation_tracks[bone_index]
            if not track:
                continue
            curve_node_id = id_gen()
            times = [kf[0] for kf in track]
            animation_curve_nodes.append(FBXAnimationCurveNode(id=curve_node_id, channel="R"))
            animation_connections.append(FBXConnection(source=curve_node_id, destination=animation_layer_id))
            animation_connections.append(
                FBXConnection(
                    src=curve_node_id,
                    dst=bone_ids[bone_index],
                    property="Lcl Rotation",
                )
            )
            for axis, label in enumerate(("X", "Y", "Z")):
                curve_id = id_gen()
                animation_curves.append(
                    FBXAnimationCurve(
                        id=curve_id,
                        key_time=[int(t * FBX_TIME_ONE_SECOND) for t in times],
                        key_value_float=[kf[1][axis] for kf in track],
                    )
                )
                animation_connections.append(
                    FBXConnection(source=curve_id, destination=curve_node_id, property=f"d|{label}")
                )

    # Connections
    connections: list[FBXConnection] = []

    # NodeAttribute -> Model
    connections.extend(
        FBXConnection(source=bone_node_attribute_ids[i], destination=bone_ids[i]) for i in range(bone_count)
    )
    connections.extend(
        FBXConnection(source=attachment_node_attribute_ids[i], destination=attachment_ids[i])
        for i in range(attachment_count)
    )

    # Bone hierarchy
    for i in range(bone_count):
        parent_fbx_id = 0 if parent_map[i] == -1 else bone_ids[parent_map[i]]
        connections.append(FBXConnection(source=bone_ids[i], destination=parent_fbx_id))

    # Attachment -> bone or scene root
    if iff.atta:
        for i, item in enumerate(iff.atta.content):
            if item.bone_index != ATTA_NO_BONE and 0 <= item.bone_index < bone_count:
                connections.append(FBXConnection(source=attachment_ids[i], destination=bone_ids[item.bone_index]))
            else:
                connections.append(FBXConnection(source=attachment_ids[i], destination=0))

    # Animation connections
    connections.extend(animation_connections)

    fbx = FBX(
        name=iff.dhna.name,
        time_stop=FBX_TIME_ONE_SECOND,
        active_anim_stack_name=iff.dhna.name,
        node_attributes=node_attributes,
        models=models,
        animation_stacks=animation_stacks,
        animation_layers=animation_layers,
        animation_curve_nodes=animation_curve_nodes,
        animation_curves=animation_curves,
        connections=connections,
        take_name=iff.dhna.name,
        take_time_stop=FBX_TIME_ONE_SECOND,
    )

    target_io, _ = fbx.model_dump_stream()
    return target_io, target_path
