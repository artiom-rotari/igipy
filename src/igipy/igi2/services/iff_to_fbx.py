"""Export IFF skeletal animation to FBX 7.5 ASCII format.

Produces a skeleton-only animation (no mesh geometry). The result can be
imported into Blender, Maya, 3ds Max, or any FBX-compatible DCC tool.
Bones are represented as LimbNode models; animation channels carry
translation and rotation keyframes extracted from TNVE entries.
"""

import logging
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

logger = logging.getLogger(__name__)

# IGI2 uses fixed-point precision: 4096 units (2^12) = 1 meter. FBX's working
# unit is centimeters (GlobalSettings UnitScaleFactor = 1), so positions must be
# emitted in centimeters: divide by 40.96 (= 4096 / 100). Dividing by 4096
# (meters) instead makes Unity/3ds Max read the model 100x too small.
SCALE = 100 / 4096

# IGI2 animation time unit: TNVE frame offsets and DHNA.duration are fixed-point ticks of
# 160 units per frame at 30 fps, i.e. 4800 ticks per second (every observed duration is a
# multiple of 160). Dividing by this maps ticks to seconds so the exported FBX timeline has
# the animation's real length instead of being squeezed into a fixed 1 second. The frame
# rate is the one empirically-fitted value; if in-engine playback is uniformly ~2x off, the
# game runs at 60 fps and this becomes 9600.
ANIMATION_TICKS_PER_SECOND = 4800.0

QUATERNION_EPSILON = 1e-10

# Euler-angle unrolling thresholds (degrees): a per-axis step larger than half a
# turn is reinterpreted as the equivalent angle one full turn away, keeping the
# rotation curve on the branch nearest the previous keyframe.
HALF_TURN_DEGREES = 180.0
FULL_TURN_DEGREES = 360.0

# bone_index = 0xABABABAB is the MSVC debug heap fill sentinel meaning "no bone"
ATTA_NO_BONE = 0xABABABAB

# Bone names from MEF MANB chunk for the 31-bone human skeleton.
# Must be byte-identical to the raw 16-byte MANB strings emitted by mef_to_fbx (names
# longer than 16 chars are truncated): FBX retargeting matches bones by exact name, so a
# full/untruncated name here silently stops that bone from receiving animation.
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
    "upper left finge",
    "upper right fing",
    "lower left finge",
    "lower right fing",
    "left fingers end",
    "right fingers en",
]

# Bone names from MEF MANB chunk for the 47-bone first-person hand skeleton.
# These MUST be byte-identical to the raw 16-byte MANB strings emitted by mef_to_fbx
# (truncated to 16 chars, trailing spaces preserved): FBX retargeting matches bones by
# exact name, so any drift here silently stops a bone from receiving animation. Trailing
# spaces on some entries are significant — do not "clean" them.
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
    "upper left ring ",  # trailing space is significant (16-byte MANB field)
    "upper left thumb",
    "upper right fore",
    "upper right litt",
    "upper right midd",
    "upper right ring",
    "upper right thum",
    "lower left foref",
    "lower left littl",
    "lower left middl",
    "lower left ring ",  # trailing space is significant (16-byte MANB field)
    "lower left thumb",
    "lower right fore",
    "lower right litt",
    "lower right midd",
    "lower right ring",
    "lower right thum",
    "left forefinger ",  # trailing space is significant (16-byte MANB field)
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
    return (
        x * inverse_length,
        y * inverse_length,
        z * inverse_length,
        w * inverse_length,
    )


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

    return (
        round(math.degrees(roll), 4),
        round(math.degrees(pitch), 4),
        round(math.degrees(yaw), 4),
    )


def _seconds_to_fbx_time(seconds: float) -> int:
    """Convert a time in seconds to FBX's integer KTime units (FBX_TIME_ONE_SECOND per second)."""
    return round(seconds * FBX_TIME_ONE_SECOND)


def _align_quaternion_signs(
    quaternions: list[tuple[float, float, float, float]],
) -> tuple[list[tuple[float, float, float, float]], int]:
    """Flip quaternions onto a common hemisphere so the track interpolates continuously.

    A quaternion and its negation describe the same orientation (the unit
    quaternion double cover), but converting each independently to Euler angles
    produces large spurious swings whenever the sign flips between keyframes.
    Negating any quaternion whose dot product with the previously kept
    quaternion is negative keeps the per-bone rotation path short. Returns the
    aligned quaternions and the number of sign flips that were applied.
    """
    aligned: list[tuple[float, float, float, float]] = []
    sign_flip_count = 0
    previous: tuple[float, float, float, float] | None = None

    for quaternion in quaternions:
        aligned_quaternion = quaternion
        if previous is not None:
            dot_product = (
                previous[0] * quaternion[0]
                + previous[1] * quaternion[1]
                + previous[2] * quaternion[2]
                + previous[3] * quaternion[3]
            )
            if dot_product < 0.0:
                aligned_quaternion = (-quaternion[0], -quaternion[1], -quaternion[2], -quaternion[3])
                sign_flip_count += 1
        aligned.append(aligned_quaternion)
        previous = aligned_quaternion

    return aligned, sign_flip_count


def _unroll_euler(
    previous_euler: tuple[float, float, float],
    euler: tuple[float, float, float],
) -> tuple[tuple[float, float, float], int]:
    """Shift Euler angles by whole turns to stay on the branch nearest the previous keyframe.

    ``atan2``/``asin`` return angles in a fixed range, so an axis that crosses
    the +/-180 degree boundary jumps by ~360 degrees and FBX's linear
    interpolation would sweep the bone the long way around. Adding or
    subtracting whole turns per axis removes that discontinuity without changing
    the orientation each keyframe represents. Returns the unrolled angles and
    the number of axes that were shifted.
    """
    unrolled = list(euler)
    unroll_count = 0

    for axis in range(3):
        shifted = False
        while unrolled[axis] - previous_euler[axis] > HALF_TURN_DEGREES:
            unrolled[axis] -= FULL_TURN_DEGREES
            shifted = True
        while unrolled[axis] - previous_euler[axis] < -HALF_TURN_DEGREES:
            unrolled[axis] += FULL_TURN_DEGREES
            shifted = True
        if shifted:
            unroll_count += 1

    return (round(unrolled[0], 4), round(unrolled[1], 4), round(unrolled[2], 4)), unroll_count


def _build_rotation_tracks(
    raw_rotation_tracks: dict[int, list[tuple[float, tuple[float, float, float, float]]]],
) -> tuple[dict[int, list[tuple[float, tuple[float, float, float]]]], int, int]:
    """Turn per-bone raw quaternion tracks into continuous Euler-angle tracks.

    For each bone the keyframes are time-sorted, the quaternions are hemisphere
    aligned, then converted to Euler angles and unrolled so consecutive
    keyframes stay on the same rotational branch. Returns the Euler tracks plus
    the total sign-flip and Euler-unroll counts for diagnostics.
    """
    rotation_tracks: dict[int, list[tuple[float, tuple[float, float, float]]]] = {}
    total_sign_flips = 0
    total_euler_unrolls = 0

    for bone_index, raw_track in raw_rotation_tracks.items():
        raw_track.sort(key=lambda keyframe: keyframe[0])
        aligned_quaternions, sign_flips = _align_quaternion_signs([quaternion for _, quaternion in raw_track])
        total_sign_flips += sign_flips

        euler_track: list[tuple[float, tuple[float, float, float]]] = []
        previous_euler: tuple[float, float, float] | None = None
        for (time_value, _), quaternion in zip(raw_track, aligned_quaternions, strict=True):
            euler = _quaternion_to_euler(*quaternion)
            if previous_euler is not None:
                euler, unrolls = _unroll_euler(previous_euler, euler)
                total_euler_unrolls += unrolls
            previous_euler = euler
            euler_track.append((time_value, euler))

        rotation_tracks[bone_index] = euler_track

    return rotation_tracks, total_sign_flips, total_euler_unrolls


def _collect_tracks(
    iff: IFF,
) -> tuple[
    dict[int, list[tuple[float, tuple[float, float, float]]]],
    dict[int, list[tuple[float, tuple[float, float, float]]]],
]:
    """Group TNVE entries into per-bone translation and rotation tracks.

    Returns (translation_tracks, rotation_tracks) where each maps
    bone_index -> sorted list of (time_normalized, values). Rotation values are
    Euler angles (degrees) for FBX, made continuous across keyframes (hemisphere
    sign alignment + Euler unrolling) so FBX's linear interpolation does not
    introduce spurious full-turn swings.

    TNVEFullTransform (0x07) and TNVEFullTransformTangent (0x01) entries are a
    separate full-transform stream and are excluded from the per-bone local TRS
    channels entirely. Both their position and their rotation are stored in a
    space that is NOT the parent-relative bone space the FBX Lcl Translation /
    Lcl Rotation curves use: feeding them in displaces root/arm bones by up to
    ~1 metre (mesh distortion) and injects 180-degree "double fire" rotation
    swings. These entries only ever appear on bones 0-9, and every bone that
    carries one also has a TNVERotation (0x04) keyframe (verified across all
    1244 files), so excluding them leaves the bone correctly driven by 0x04
    rotation plus 0x03 position; a bone with no 0x03 keyframe simply holds its
    REIH rest offset, which is correct for a skeletal rig.
    """
    translation_tracks: dict[int, list[tuple[float, tuple[float, float, float]]]] = defaultdict(list)
    raw_rotation_tracks: dict[int, list[tuple[float, tuple[float, float, float, float]]]] = defaultdict(list)
    excluded_full_transform_entries = 0

    for entry in iff.tnve.content:
        if isinstance(entry, TNVESeparator):
            break

        # Real elapsed seconds for this keyframe (NOT normalized to a fixed 1-second clip).
        time_seconds = entry.frame_offset / ANIMATION_TICKS_PER_SECOND

        if isinstance(entry, TNVEPosition):
            position = _position_to_fbx(entry.position_x, entry.position_y, entry.position_z)
            translation_tracks[entry.bone_index].append((time_seconds, position))
        elif isinstance(entry, TNVETrigger):
            pass
        elif isinstance(entry, TNVERotation):
            quaternion = _quaternion_to_fbx(
                entry.quaternion_x,
                entry.quaternion_y,
                entry.quaternion_z,
                entry.quaternion_w,
            )
            raw_rotation_tracks[entry.bone_index].append((time_seconds, quaternion))
        elif isinstance(entry, TNVEFullTransform | TNVEFullTransformTangent):
            # Separate full-transform stream in non-local space — excluded from local TRS.
            excluded_full_transform_entries += 1

    for track in translation_tracks.values():
        track.sort(key=lambda keyframe: keyframe[0])

    rotation_tracks, total_sign_flips, total_euler_unrolls = _build_rotation_tracks(raw_rotation_tracks)

    logger.debug(
        "[FIX] iff_to_fbx track cleanup: animation=%s sign_flip_corrections=%d euler_unrolls=%d "
        "full_transform_entries_excluded=%d",
        iff.dhna.name,
        total_sign_flips,
        total_euler_unrolls,
        excluded_full_transform_entries,
    )

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
            FBXNodeAttribute(
                id=bone_node_attribute_ids[i],
                name=name,
                type="LimbNode",
                type_flags="Skeleton",
            ),
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
                FBXNodeAttribute(
                    id=attachment_node_attribute_ids[i],
                    name=name,
                    type="Null",
                    type_flags="Null",
                ),
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
                    source=curve_node_id,
                    destination=bone_ids[bone_index],
                    property="Lcl Translation",
                )
            )
            for axis, label in enumerate(("X", "Y", "Z")):
                curve_id = id_gen()
                animation_curves.append(
                    FBXAnimationCurve(
                        id=curve_id,
                        key_time=[_seconds_to_fbx_time(t) for t in times],
                        key_value_float=[kf[1][axis] for kf in track],
                    )
                )
                animation_connections.append(
                    FBXConnection(
                        source=curve_id,
                        destination=curve_node_id,
                        property=f"d|{label}",
                    )
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
                    source=curve_node_id,
                    destination=bone_ids[bone_index],
                    property="Lcl Rotation",
                )
            )
            for axis, label in enumerate(("X", "Y", "Z")):
                curve_id = id_gen()
                animation_curves.append(
                    FBXAnimationCurve(
                        id=curve_id,
                        key_time=[_seconds_to_fbx_time(t) for t in times],
                        key_value_float=[kf[1][axis] for kf in track],
                    )
                )
                animation_connections.append(
                    FBXConnection(
                        source=curve_id,
                        destination=curve_node_id,
                        property=f"d|{label}",
                    )
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

    # Scale the FBX timeline to the clip's real length instead of a fixed 1 second so playback
    # speed matches the game (long clips were previously squeezed into 1s and played too fast).
    animation_duration_seconds = iff.dhna.duration / ANIMATION_TICKS_PER_SECOND
    animation_time_stop = _seconds_to_fbx_time(animation_duration_seconds)
    logger.debug(
        "[FIX] iff_to_fbx timeline: animation=%s duration_ticks=%d duration_seconds=%.3f",
        iff.dhna.name,
        iff.dhna.duration,
        animation_duration_seconds,
    )

    fbx = FBX(
        name=iff.dhna.name,
        time_stop=animation_time_stop,
        active_anim_stack_name=iff.dhna.name,
        node_attributes=node_attributes,
        models=models,
        animation_stacks=animation_stacks,
        animation_layers=animation_layers,
        animation_curve_nodes=animation_curve_nodes,
        animation_curves=animation_curves,
        connections=connections,
        take_name=iff.dhna.name,
        take_time_stop=animation_time_stop,
    )

    target_io, _ = fbx.model_dump_stream()
    return target_io, target_path
