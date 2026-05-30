"""Export IFF skeletal animation to a self-contained glTF 2.0 file.

Produces a skeleton-only animation (no mesh geometry). The result can be
viewed in Blender, VS Code, glTF Tools, or any glTF-compatible viewer.
Bones are represented as nodes; animation channels carry translation and
rotation keyframes extracted from TNVE entries.
"""

import base64
import json
import math
import struct
from collections import defaultdict
from io import BytesIO
from pathlib import Path

from igipy.igi2.formats.iff import (
    IFF,
    TNVEFullTransform,
    TNVEFullTransformTangent,
    TNVEPosition,
    TNVERotation,
    TNVESeparator,
    TNVETrigger,
)

# glTF component/accessor type constants
FLOAT = 5126
UNSIGNED_SHORT = 5123

# IGI2 uses fixed-point precision: 4096 units (2^12) = 1 meter.
# The 31-bone skeleton measures ~7319 units from foot to head end,
# producing 1.787m (5'10") — the standard male character height.
SCALE = 1 / 4096

# Quaternion normalization threshold — magnitudes below this are treated as zero.
QUATERNION_EPSILON = 1e-10

# bone_index = 0xABABABAB is the MSVC debug heap fill sentinel meaning "no bone"
ATTA_NO_BONE = 0xABABABAB

# Coordinate system conversion: IGI2 uses Z-up (X=right, Y=forward, Z=up),
# glTF uses Y-up right-handed (X=right, Y=up, -Z=forward).
# Transform: (x, y, z) → (x, z, -y) for positions,
#            (qx, qy, qz, qw) → (qx, qz, -qy, qw) for quaternions.


def _position_to_gltf(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Convert a position from IGI2 Z-up to glTF Y-up coordinates."""
    return x * SCALE, z * SCALE, -y * SCALE


def _quaternion_to_gltf(x: float, y: float, z: float, w: float) -> tuple[float, float, float, float]:
    """Convert a quaternion from IGI2 Z-up to glTF Y-up coordinates."""
    return _normalize_quaternion(x, z, -y, w)


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


def _normalize_quaternion(x: float, y: float, z: float, w: float) -> tuple[float, float, float, float]:
    """Normalize a quaternion to unit length. Returns identity if zero-length."""
    length = math.sqrt(x * x + y * y + z * z + w * w)
    if length < QUATERNION_EPSILON:
        return 0.0, 0.0, 0.0, 1.0
    inverse_length = 1.0 / length
    return x * inverse_length, y * inverse_length, z * inverse_length, w * inverse_length


def _make_data_uri(raw: bytes) -> str:
    """Encode raw bytes as a base64 data URI for an embedded glTF buffer."""
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:application/octet-stream;base64,{encoded}"


def _collect_tracks(
    iff: IFF,
) -> tuple[
    dict[int, list[tuple[float, tuple[float, float, float]]]],
    dict[int, list[tuple[float, tuple[float, float, float, float]]]],
]:
    """Group TNVE entries into per-bone translation and rotation tracks.

    Returns:
        (translation_tracks, rotation_tracks) where each maps
        bone_index -> sorted list of (time, values).
    """
    duration = max(iff.dhna.duration, 1)

    translation_tracks: dict[int, list[tuple[float, tuple[float, float, float]]]] = defaultdict(list)
    rotation_tracks: dict[int, list[tuple[float, tuple[float, float, float, float]]]] = defaultdict(list)

    for entry in iff.tnve.content:
        if isinstance(entry, TNVESeparator):
            # Loop boundary: everything after this is wrap-around pose data
            # for seamless loop blending, not regular animation keyframes.
            break

        t = entry.frame_offset / duration

        if isinstance(entry, TNVEPosition):
            translation_tracks[entry.bone_index].append(
                (t, _position_to_gltf(entry.position_x, entry.position_y, entry.position_z))
            )

        elif isinstance(entry, TNVETrigger):
            # Type 0x06 entries are trigger events (sound, FX, etc.), not
            # animation keyframes. Their position is world-space trigger
            # location, not bone-space pose data. Skip for skeletal export.
            pass

        elif isinstance(entry, TNVERotation):
            rotation_tracks[entry.bone_index].append(
                (t, _quaternion_to_gltf(entry.quaternion_x, entry.quaternion_y, entry.quaternion_z, entry.quaternion_w))
            )

        elif isinstance(entry, TNVEFullTransform):
            translation_tracks[entry.bone_index].append(
                (t, _position_to_gltf(entry.position_x, entry.position_y, entry.position_z))
            )
            rotation_tracks[entry.bone_index].append(
                (t, _quaternion_to_gltf(entry.quaternion_x, entry.quaternion_y, entry.quaternion_z, entry.quaternion_w))
            )

        elif isinstance(entry, TNVEFullTransformTangent):
            translation_tracks[entry.bone_index].append(
                (t, _position_to_gltf(entry.position_x, entry.position_y, entry.position_z))
            )
            rotation_tracks[entry.bone_index].append(
                (
                    t,
                    _quaternion_to_gltf(
                        entry.quaternion_a_x, entry.quaternion_a_y, entry.quaternion_a_z, entry.quaternion_a_w
                    ),
                )
            )

    # Sort each track by time
    for track in translation_tracks.values():
        track.sort(key=lambda x: x[0])
    for track in rotation_tracks.values():
        track.sort(key=lambda x: x[0])

    return translation_tracks, rotation_tracks


class _GltfBufferBuilder:
    """Accumulates binary buffer data and builds glTF accessors/bufferViews."""

    def __init__(self) -> None:
        self.buffer = bytearray()
        self.buffer_views: list[dict] = []
        self.accessors: list[dict] = []

    def add_scalar_accessor(self, times: list[float]) -> int:
        """Append a SCALAR float accessor and return its index."""
        offset = len(self.buffer)
        for t in times:
            self.buffer.extend(struct.pack("<f", t))
        byte_length = len(self.buffer) - offset
        buffer_view_index = len(self.buffer_views)
        self.buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": byte_length})
        accessor_index = len(self.accessors)
        self.accessors.append(
            {
                "bufferView": buffer_view_index,
                "componentType": FLOAT,
                "count": len(times),
                "type": "SCALAR",
                "min": [min(times)],
                "max": [max(times)],
            }
        )
        return accessor_index

    def add_vec3_accessor(self, values: list[tuple[float, float, float]]) -> int:
        """Append a VEC3 float accessor and return its index."""
        offset = len(self.buffer)
        for v in values:
            self.buffer.extend(struct.pack("<3f", *v))
        byte_length = len(self.buffer) - offset
        buffer_view_index = len(self.buffer_views)
        self.buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": byte_length})
        accessor_index = len(self.accessors)
        mins = [min(v[i] for v in values) for i in range(3)]
        maxs = [max(v[i] for v in values) for i in range(3)]
        self.accessors.append(
            {
                "bufferView": buffer_view_index,
                "componentType": FLOAT,
                "count": len(values),
                "type": "VEC3",
                "min": mins,
                "max": maxs,
            }
        )
        return accessor_index

    def add_vec4_accessor(self, values: list[tuple[float, float, float, float]]) -> int:
        """Append a VEC4 float accessor and return its index."""
        offset = len(self.buffer)
        for v in values:
            self.buffer.extend(struct.pack("<4f", *v))
        byte_length = len(self.buffer) - offset
        buffer_view_index = len(self.buffer_views)
        self.buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": byte_length})
        accessor_index = len(self.accessors)
        mins = [min(v[i] for v in values) for i in range(4)]
        maxs = [max(v[i] for v in values) for i in range(4)]
        self.accessors.append(
            {
                "bufferView": buffer_view_index,
                "componentType": FLOAT,
                "count": len(values),
                "type": "VEC4",
                "min": mins,
                "max": maxs,
            }
        )
        return accessor_index


def _add_attachment_nodes(iff: IFF, nodes: list[dict], bone_count: int) -> list[int]:
    """Add ATTA attachment point nodes and return indices of unparented ones."""
    unparented: list[int] = []
    if not iff.atta:
        return unparented

    for item in iff.atta.content:
        name = item.name.rstrip(b"\x00").decode("ascii", errors="replace")
        attachment_node: dict = {
            "name": f"attach_{name}",
            "translation": list(_position_to_gltf(item.position_x, item.position_y, item.position_z)),
            "rotation": list(
                _quaternion_to_gltf(item.orientation_x, item.orientation_y, item.orientation_z, item.orientation_w)
            ),
        }
        attachment_index = len(nodes)
        nodes.append(attachment_node)
        if item.bone_index != ATTA_NO_BONE and 0 <= item.bone_index < bone_count:
            nodes[item.bone_index].setdefault("children", []).append(attachment_index)
        else:
            unparented.append(attachment_index)

    return unparented


def _build_skeleton_nodes(iff: IFF, bone_count: int) -> tuple[list[dict], list[int]]:
    """Build glTF node list from skeleton hierarchy and attachment points.

    Returns (nodes, scene_nodes) where scene_nodes lists root-level node indices.
    """
    parent_map = iff.reih.bones_parents
    raw_offsets = iff.reih.bones_offsets
    bone_names = _BONE_NAMES_31 if bone_count == len(_BONE_NAMES_31) else None

    nodes: list[dict] = []
    for i in range(bone_count):
        name = bone_names[i] if bone_names and i < len(bone_names) else f"bone_{i:03d}"
        node: dict = {"name": name}
        if i < len(raw_offsets):
            ox, oy, oz = raw_offsets[i]
            node["translation"] = list(_position_to_gltf(ox, oy, oz))
        nodes.append(node)

    # Build children lists from parent map
    for i in range(bone_count):
        parent_idx = parent_map[i]
        if 0 <= parent_idx < bone_count:
            nodes[parent_idx].setdefault("children", []).append(i)

    # Attachment points + unparented attachment scene nodes
    unparented_attachments = _add_attachment_nodes(iff, nodes, bone_count)

    # Scene nodes: root bones + unparented attachments
    scene_nodes = [i for i in range(bone_count) if parent_map[i] == -1]
    scene_nodes.extend(unparented_attachments)

    return nodes, scene_nodes


def _build_animation(
    builder: _GltfBufferBuilder,
    translation_tracks: dict[int, list[tuple[float, tuple[float, float, float]]]],
    rotation_tracks: dict[int, list[tuple[float, tuple[float, float, float, float]]]],
    bone_count: int,
) -> tuple[list[dict], list[dict]]:
    """Build glTF animation channels and samplers from keyframe tracks.

    Returns (channels, samplers).
    """
    channels: list[dict] = []
    samplers: list[dict] = []

    for bone_idx, track in sorted(translation_tracks.items()):
        if bone_idx >= bone_count or not track:
            continue
        times = [kf[0] for kf in track]
        values = [kf[1] for kf in track]
        time_acc = builder.add_scalar_accessor(times)
        value_acc = builder.add_vec3_accessor(values)
        sampler_idx = len(samplers)
        samplers.append({"input": time_acc, "output": value_acc, "interpolation": "LINEAR"})
        channels.append({"sampler": sampler_idx, "target": {"node": bone_idx, "path": "translation"}})

    for bone_idx, track in sorted(rotation_tracks.items()):
        if bone_idx >= bone_count or not track:
            continue
        times = [kf[0] for kf in track]
        values = [kf[1] for kf in track]
        time_acc = builder.add_scalar_accessor(times)
        value_acc = builder.add_vec4_accessor(values)
        sampler_idx = len(samplers)
        samplers.append({"input": time_acc, "output": value_acc, "interpolation": "LINEAR"})
        channels.append({"sampler": sampler_idx, "target": {"node": bone_idx, "path": "rotation"}})

    return channels, samplers


def iff_to_gltf(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_path: Path | None = source_path.with_suffix(".gltf") if source_path is not None else None
    iff = IFF.model_validate_stream(source_io)

    bone_count = iff.dhna.bone_count
    translation_tracks, rotation_tracks = _collect_tracks(iff)

    builder = _GltfBufferBuilder()
    nodes, scene_nodes = _build_skeleton_nodes(iff, bone_count)
    channels, samplers = _build_animation(builder, translation_tracks, rotation_tracks, bone_count)

    # Assemble glTF
    gltf: dict = {
        "asset": {"version": "2.0", "generator": "igipy"},
        "scene": 0,
        "scenes": [{"name": iff.dhna.name, "nodes": scene_nodes}],
        "nodes": nodes,
    }

    if channels:
        gltf["animations"] = [{"name": iff.dhna.name, "channels": channels, "samplers": samplers}]

    if builder.buffer_views:
        buffer_bytes = bytes(builder.buffer)
        gltf["buffers"] = [{"uri": _make_data_uri(buffer_bytes), "byteLength": len(buffer_bytes)}]
        gltf["bufferViews"] = builder.buffer_views
        gltf["accessors"] = builder.accessors

    target_io = BytesIO()
    target_io.write(json.dumps(gltf, indent=2).encode("utf-8"))
    target_io.seek(0)
    return target_io, target_path
