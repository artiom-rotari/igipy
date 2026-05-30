"""Export IFF skeletal animation to a self-contained glTF 2.0 file.

Produces a skeleton-only animation (no mesh geometry). The result can be
viewed in Blender, VS Code glTF Tools, or any glTF-compatible viewer.
Bones are represented as nodes; animation channels carry translation and
rotation keyframes extracted from TNVE entries.
"""

import base64
import json
import math
import struct
from collections import defaultdict, deque
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

# Coordinate system conversion: IGI2 uses Z-up (X=right, Y=forward, Z=up),
# glTF uses Y-up right-handed (X=right, Y=up, -Z=forward).
# Transform: (x, y, z) → (x, z, -y) for positions,
#            (qx, qy, qz, qw) → (qx, qz, -qy, qw) for quaternions.


def _pos_to_gltf(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Convert a position from IGI2 Z-up to glTF Y-up coordinates."""
    return (x * SCALE, z * SCALE, -y * SCALE)


def _quat_to_gltf(x: float, y: float, z: float, w: float) -> tuple[float, float, float, float]:
    """Convert a quaternion from IGI2 Z-up to glTF Y-up coordinates."""
    return _normalize_quat(x, z, -y, w)


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


def _build_parent_map(child_counts: list[int]) -> list[int]:
    """Reconstruct parent indices from BFS-ordered child counts.

    REIH bone_child_counts are the out-degree (number of direct children)
    for each bone, listed in breadth-first order. The sum of all counts equals
    N-1 (every bone except the root has exactly one parent).

    The algorithm uses a FIFO queue: each bone is dequeued once all its children
    have been assigned, and each new bone with children > 0 is enqueued.
    """
    n = len(child_counts)
    parents = [-1] * n
    if n <= 1:
        return parents
    queue: deque[list[int]] = deque()
    queue.append([0, child_counts[0]])  # [bone_index, remaining_children]
    bone_idx = 1
    while queue and bone_idx < n:
        front = queue[0]
        if front[1] == 0:
            queue.popleft()
            continue
        parents[bone_idx] = front[0]
        front[1] -= 1
        if child_counts[bone_idx] > 0:
            queue.append([bone_idx, child_counts[bone_idx]])
        bone_idx += 1
    return parents


def _normalize_quat(x: float, y: float, z: float, w: float) -> tuple[float, float, float, float]:
    """Normalize a quaternion to unit length. Returns identity if zero-length."""
    length = math.sqrt(x * x + y * y + z * z + w * w)
    if length < 1e-10:
        return (0.0, 0.0, 0.0, 1.0)
    inv = 1.0 / length
    return (x * inv, y * inv, z * inv, w * inv)


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

    trans: dict[int, list[tuple[float, tuple[float, float, float]]]] = defaultdict(list)
    rots: dict[int, list[tuple[float, tuple[float, float, float, float]]]] = defaultdict(list)

    for entry in iff.tnve.content:
        if isinstance(entry, TNVESeparator):
            # Loop boundary: everything after this is wrap-around pose data
            # for seamless loop blending, not regular animation keyframes.
            break

        t = entry.frame_offset / duration

        if isinstance(entry, TNVEPosition):
            trans[entry.bone_index].append((t, _pos_to_gltf(entry.position_x, entry.position_y, entry.position_z)))

        elif isinstance(entry, TNVETrigger):
            # Type 0x06 entries are trigger events (sound, FX, etc.), not
            # animation keyframes. Their position is world-space trigger
            # location, not bone-space pose data. Skip for skeletal export.
            pass

        elif isinstance(entry, TNVERotation):
            rots[entry.bone_index].append(
                (t, _quat_to_gltf(entry.quaternion_x, entry.quaternion_y, entry.quaternion_z, entry.quaternion_w))
            )

        elif isinstance(entry, TNVEFullTransform):
            trans[entry.bone_index].append((t, _pos_to_gltf(entry.position_x, entry.position_y, entry.position_z)))
            rots[entry.bone_index].append(
                (t, _quat_to_gltf(entry.quaternion_x, entry.quaternion_y, entry.quaternion_z, entry.quaternion_w))
            )

        elif isinstance(entry, TNVEFullTransformTangent):
            trans[entry.bone_index].append((t, _pos_to_gltf(entry.position_x, entry.position_y, entry.position_z)))
            rots[entry.bone_index].append(
                (
                    t,
                    _quat_to_gltf(
                        entry.quaternion_a_x, entry.quaternion_a_y, entry.quaternion_a_z, entry.quaternion_a_w
                    ),
                )
            )

    # Sort each track by time
    for track in trans.values():
        track.sort(key=lambda x: x[0])
    for track in rots.values():
        track.sort(key=lambda x: x[0])

    return trans, rots


def iff_to_gltf(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_path: Path | None = source_path.with_suffix(".gltf") if source_path is not None else None
    iff = IFF.model_validate_stream(source_io)

    bone_count = iff.dhna.bone_count
    trans_tracks, rot_tracks = _collect_tracks(iff)

    # --- Build binary buffer ---
    buf = bytearray()
    buffer_views: list[dict] = []
    accessors: list[dict] = []

    def add_scalar_accessor(times: list[float]) -> int:
        """Append a SCALAR float accessor and return its index."""
        offset = len(buf)
        for t in times:
            buf.extend(struct.pack("<f", t))
        byte_length = len(buf) - offset
        bv_idx = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": byte_length})
        acc_idx = len(accessors)
        accessors.append(
            {
                "bufferView": bv_idx,
                "componentType": FLOAT,
                "count": len(times),
                "type": "SCALAR",
                "min": [min(times)],
                "max": [max(times)],
            }
        )
        return acc_idx

    def add_vec3_accessor(values: list[tuple[float, float, float]]) -> int:
        """Append a VEC3 float accessor and return its index."""
        offset = len(buf)
        for v in values:
            buf.extend(struct.pack("<3f", *v))
        byte_length = len(buf) - offset
        bv_idx = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": byte_length})
        acc_idx = len(accessors)
        mins = [min(v[i] for v in values) for i in range(3)]
        maxs = [max(v[i] for v in values) for i in range(3)]
        accessors.append(
            {
                "bufferView": bv_idx,
                "componentType": FLOAT,
                "count": len(values),
                "type": "VEC3",
                "min": mins,
                "max": maxs,
            }
        )
        return acc_idx

    def add_vec4_accessor(values: list[tuple[float, float, float, float]]) -> int:
        """Append a VEC4 float accessor and return its index."""
        offset = len(buf)
        for v in values:
            buf.extend(struct.pack("<4f", *v))
        byte_length = len(buf) - offset
        bv_idx = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": byte_length})
        acc_idx = len(accessors)
        mins = [min(v[i] for v in values) for i in range(4)]
        maxs = [max(v[i] for v in values) for i in range(4)]
        accessors.append(
            {
                "bufferView": bv_idx,
                "componentType": FLOAT,
                "count": len(values),
                "type": "VEC4",
                "min": mins,
                "max": maxs,
            }
        )
        return acc_idx

    # --- Nodes: one per bone, using the correct tree hierarchy ---
    # REIH rest-pose offsets are already parent-relative (bone-local translations).
    # Evidence: bones 10-12 (rotation helpers) have (0,0,0) = co-located with parent,
    # and offsets for bones 1-30 stay constant across animations while bone 0 varies.
    parent_map = _build_parent_map(iff.reih.bone_child_counts)
    raw_offsets = list(iff.reih.rest_pose_offsets) if iff.reih.rest_pose_offsets else []
    bone_names = _BONE_NAMES_31 if bone_count == 31 else None

    nodes: list[dict] = []
    for i in range(bone_count):
        name = bone_names[i] if bone_names and i < len(bone_names) else f"bone_{i:03d}"
        node: dict = {"name": name}
        if i < len(raw_offsets):
            ox, oy, oz = raw_offsets[i]
            node["translation"] = list(_pos_to_gltf(ox, oy, oz))
        nodes.append(node)

    # Build children lists from parent map
    for i in range(bone_count):
        parent_idx = parent_map[i]
        if 0 <= parent_idx < bone_count:
            nodes[parent_idx].setdefault("children", []).append(i)

    # Attachment point nodes (after bone nodes, parented to their bone)
    # bone_index = 0xABABABAB is the MSVC debug heap fill sentinel meaning "no bone"
    _ATTA_NO_BONE = 0xABABABAB
    if iff.atta:
        for item in iff.atta.content:
            name = item.name.rstrip(b"\x00").decode("ascii", errors="replace")
            att_node: dict = {
                "name": f"attach_{name}",
                "translation": list(_pos_to_gltf(item.position_x, item.position_y, item.position_z)),
                "rotation": list(
                    _quat_to_gltf(item.orientation_x, item.orientation_y, item.orientation_z, item.orientation_w)
                ),
            }
            att_idx = len(nodes)
            nodes.append(att_node)
            if item.bone_index != _ATTA_NO_BONE and 0 <= item.bone_index < bone_count:
                nodes[item.bone_index].setdefault("children", []).append(att_idx)

    # --- Scene: only root bones are scene nodes, rest are children ---
    scene_nodes = [i for i in range(bone_count) if parent_map[i] == -1]
    # Add unparented attachment nodes (no-bone sentinel or bone_index out of range)
    if iff.atta:
        for i, item in enumerate(iff.atta.content):
            att_idx = bone_count + i
            if item.bone_index == _ATTA_NO_BONE or item.bone_index < 0 or item.bone_index >= bone_count:
                scene_nodes.append(att_idx)

    # --- Animation channels + samplers ---
    channels: list[dict] = []
    samplers: list[dict] = []

    for bone_idx, track in sorted(trans_tracks.items()):
        if bone_idx >= bone_count or not track:
            continue
        times = [kf[0] for kf in track]
        values = [kf[1] for kf in track]
        time_acc = add_scalar_accessor(times)
        value_acc = add_vec3_accessor(values)
        sampler_idx = len(samplers)
        samplers.append({"input": time_acc, "output": value_acc, "interpolation": "LINEAR"})
        channels.append({"sampler": sampler_idx, "target": {"node": bone_idx, "path": "translation"}})

    for bone_idx, track in sorted(rot_tracks.items()):
        if bone_idx >= bone_count or not track:
            continue
        times = [kf[0] for kf in track]
        values = [kf[1] for kf in track]
        time_acc = add_scalar_accessor(times)
        value_acc = add_vec4_accessor(values)
        sampler_idx = len(samplers)
        samplers.append({"input": time_acc, "output": value_acc, "interpolation": "LINEAR"})
        channels.append({"sampler": sampler_idx, "target": {"node": bone_idx, "path": "rotation"}})

    # --- Assemble glTF ---
    gltf: dict = {
        "asset": {"version": "2.0", "generator": "igipy"},
        "scene": 0,
        "scenes": [{"name": iff.dhna.name, "nodes": scene_nodes}],
        "nodes": nodes,
    }

    if channels:
        gltf["animations"] = [{"name": iff.dhna.name, "channels": channels, "samplers": samplers}]

    if buffer_views:
        buf_bytes = bytes(buf)
        gltf["buffers"] = [{"uri": _make_data_uri(buf_bytes), "byteLength": len(buf_bytes)}]
        gltf["bufferViews"] = buffer_views
        gltf["accessors"] = accessors

    target_io = BytesIO()
    target_io.write(json.dumps(gltf, indent=2).encode("utf-8"))
    target_io.seek(0)
    return target_io, target_path
