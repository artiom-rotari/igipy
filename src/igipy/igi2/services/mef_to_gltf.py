"""Export MEF 3D model to a self-contained glTF 2.0 file.

Produces a triangle mesh with positions, normals, UVs, and per-render-group
primitives. Skeletal models (type 1) include a bone hierarchy, skinning
weights, and attachment points. Static (type 0) and building (type 3) models
export geometry only. SEMS variant files export simplified collision geometry.

The result can be viewed in Blender, VS Code glTF Tools, or any glTF viewer.
"""

import base64
import json
import struct
from io import BytesIO
from pathlib import Path

from igipy.igi2.formats.mef import MEF

# glTF component type constants
FLOAT = 5126
UNSIGNED_SHORT = 5123
UNSIGNED_INT = 5125

# IGI2 fixed-point scale: 4096 units = 1 meter.
SCALE = 1 / 4096

# ATTA sentinel for "no bone"
ATTA_NO_BONE = 0xABABABAB

UNSIGNED_SHORT_MAX = 65536
DETERMINANT_EPSILON = 1e-15

MODEL_TYPE_STATIC = 0
MODEL_TYPE_SKELETAL = 1
MODEL_TYPE_BUILDING = 3


def _position_to_gltf(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Convert position from IGI2 Z-up to glTF Y-up: (x,y,z) → (x,z,-y)."""
    return x * SCALE, z * SCALE, -y * SCALE


def _normal_to_gltf(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Convert normal vector from IGI2 Z-up to glTF Y-up (no scale)."""
    return x, z, -y


def _make_data_uri(raw: bytes) -> str:
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:application/octet-stream;base64,{encoded}"


class _GltfBufferBuilder:
    """Accumulates binary buffer data and builds glTF accessors/bufferViews."""

    def __init__(self) -> None:
        self.buffer = bytearray()
        self.buffer_views: list[dict] = []
        self.accessors: list[dict] = []

    def _align(self, alignment: int = 4) -> None:
        """Pad buffer to the given alignment boundary."""
        padding = (alignment - len(self.buffer) % alignment) % alignment
        self.buffer.extend(b"\x00" * padding)

    def add_scalar_accessor(self, values: list[float], *, component_type: int = FLOAT) -> int:
        self._align()
        offset = len(self.buffer)
        for v in values:
            self.buffer.extend(struct.pack("<f", v))
        byte_length = len(self.buffer) - offset
        buffer_view_index = len(self.buffer_views)
        self.buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": byte_length})
        accessor_index = len(self.accessors)
        self.accessors.append(
            {
                "bufferView": buffer_view_index,
                "componentType": component_type,
                "count": len(values),
                "type": "SCALAR",
                "min": [min(values)],
                "max": [max(values)],
            }
        )
        return accessor_index

    def add_vec2_accessor(self, values: list[tuple[float, float]]) -> int:
        self._align()
        offset = len(self.buffer)
        for v in values:
            self.buffer.extend(struct.pack("<2f", *v))
        byte_length = len(self.buffer) - offset
        buffer_view_index = len(self.buffer_views)
        self.buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": byte_length})
        accessor_index = len(self.accessors)
        mins = [min(v[i] for v in values) for i in range(2)]
        maxs = [max(v[i] for v in values) for i in range(2)]
        self.accessors.append(
            {
                "bufferView": buffer_view_index,
                "componentType": FLOAT,
                "count": len(values),
                "type": "VEC2",
                "min": mins,
                "max": maxs,
            }
        )
        return accessor_index

    def add_vec3_accessor(self, values: list[tuple[float, float, float]]) -> int:
        self._align()
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
        self._align()
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

    def add_vec4_u16_accessor(self, values: list[tuple[int, int, int, int]]) -> int:
        """Add a VEC4 accessor with UNSIGNED_SHORT components (for joint indices)."""
        self._align()
        offset = len(self.buffer)
        for v in values:
            self.buffer.extend(struct.pack("<4H", *v))
        byte_length = len(self.buffer) - offset
        buffer_view_index = len(self.buffer_views)
        self.buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": byte_length})
        accessor_index = len(self.accessors)
        mins = [min(v[i] for v in values) for i in range(4)]
        maxs = [max(v[i] for v in values) for i in range(4)]
        self.accessors.append(
            {
                "bufferView": buffer_view_index,
                "componentType": UNSIGNED_SHORT,
                "count": len(values),
                "type": "VEC4",
                "min": mins,
                "max": maxs,
            }
        )
        return accessor_index

    def add_mat4_accessor(self, matrices: list[list[float]]) -> int:
        self._align()
        offset = len(self.buffer)
        for m in matrices:
            self.buffer.extend(struct.pack("<16f", *m))
        byte_length = len(self.buffer) - offset
        buffer_view_index = len(self.buffer_views)
        self.buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": byte_length})
        accessor_index = len(self.accessors)
        self.accessors.append(
            {
                "bufferView": buffer_view_index,
                "componentType": FLOAT,
                "count": len(matrices),
                "type": "MAT4",
            }
        )
        return accessor_index

    def add_indices_accessor(self, indices: list[int]) -> int:
        """Add face index data. Uses UNSIGNED_SHORT if all < 65536, else UNSIGNED_INT."""
        self._align()
        offset = len(self.buffer)
        maximum_value = max(indices) if indices else 0
        if maximum_value < UNSIGNED_SHORT_MAX:
            component_type = UNSIGNED_SHORT
            for idx in indices:
                self.buffer.extend(struct.pack("<H", idx))
        else:
            component_type = UNSIGNED_INT
            for idx in indices:
                self.buffer.extend(struct.pack("<I", idx))
        byte_length = len(self.buffer) - offset
        buffer_view_index = len(self.buffer_views)
        self.buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": byte_length})
        accessor_index = len(self.accessors)
        self.accessors.append(
            {
                "bufferView": buffer_view_index,
                "componentType": component_type,
                "count": len(indices),
                "type": "SCALAR",
                "min": [min(indices)] if indices else [0],
                "max": [max(indices)] if indices else [0],
            }
        )
        return accessor_index


def _build_skeleton(  # noqa: C901
    mef: MEF, builder: _GltfBufferBuilder
) -> tuple[list[dict], list[int], dict | None, list[list[float]]]:
    """Build skeleton nodes, scene roots, skin object, and world transforms.

    Returns (nodes, scene_root_indices, skin_dict_or_None, world_transforms).
    world_transforms[i] is the 4x4 column-major world matrix for bone i.
    """
    if mef.reih is None or mef.manb is None:
        return [], [], None, []

    rest_offsets = mef.reih.bones_offsets
    bone_count = len(mef.reih.content)
    parents = mef.reih.bones_parents
    names = mef.manb.content[:bone_count]

    nodes: list[dict] = []
    for i in range(bone_count):
        node: dict = {"name": names[i] if i < len(names) else f"bone_{i:03d}"}
        if i < len(rest_offsets):
            offset_x, offset_y, offset_z = rest_offsets[i]
            node["translation"] = list(_position_to_gltf(offset_x, offset_y, offset_z))
        nodes.append(node)

    # Build children lists
    for i in range(bone_count):
        parent_index = parents[i]
        if 0 <= parent_index < bone_count:
            nodes[parent_index].setdefault("children", []).append(i)

    # Compute world transforms for inverse bind matrices
    world_transforms: list[list[float]] = []
    for i in range(bone_count):
        t = nodes[i].get("translation", [0, 0, 0])
        # Local transform is just a translation (no rotation in rest pose)
        local = [
            1,
            0,
            0,
            0,
            0,
            1,
            0,
            0,
            0,
            0,
            1,
            0,
            t[0],
            t[1],
            t[2],
            1,
        ]
        parent_index = parents[i]
        if 0 <= parent_index < len(world_transforms):
            parent_world = world_transforms[parent_index]
            world = _mat4_mul(parent_world, local)
        else:
            world = local
        world_transforms.append(world)

    # Inverse bind matrices
    inverse_bind_matrices = [_mat4_inverse(wt) for wt in world_transforms]
    inverse_bind_matrices_accessor = builder.add_mat4_accessor(inverse_bind_matrices)

    # Add attachment nodes
    unparented_attachments: list[int] = []
    if mef.atta is not None:
        for item in mef.atta.content:
            name = item.name.rstrip(b"\x00").decode("ascii", errors="replace")
            attachment_node: dict = {
                "name": f"attach_{name}",
                "translation": list(_position_to_gltf(item.position_x, item.position_y, item.position_z)),
            }
            attachment_index = len(nodes)
            nodes.append(attachment_node)
            if item.bone_index != ATTA_NO_BONE and 0 <= item.bone_index < bone_count:
                nodes[item.bone_index].setdefault("children", []).append(attachment_index)
            else:
                unparented_attachments.append(attachment_index)

    # Scene roots: bones without parents + unparented attachments
    scene_roots = [i for i in range(bone_count) if parents[i] == -1]
    scene_roots.extend(unparented_attachments)

    joints = list(range(bone_count))
    skin: dict = {
        "joints": joints,
        "skeleton": scene_roots[0] if scene_roots else 0,
        "inverseBindMatrices": inverse_bind_matrices_accessor,
    }

    return nodes, scene_roots, skin, world_transforms


def _mat4_mul(a: list[float], b: list[float]) -> list[float]:
    """Multiply two 4x4 column-major matrices."""
    result = [0.0] * 16
    for row in range(4):
        for col in range(4):
            s = 0.0
            for k in range(4):
                s += a[row + k * 4] * b[k + col * 4]
            result[row + col * 4] = s
    return result


def _mat4_inverse(m: list[float]) -> list[float]:
    """Invert a 4x4 column-major matrix. Falls back to identity on singular."""
    # For translation-only matrices (common for rest poses), this is straightforward.
    # Using cofactor expansion for the general case.
    inv = [0.0] * 16

    inv[0] = (
        m[5] * m[10] * m[15]
        - m[5] * m[11] * m[14]
        - m[9] * m[6] * m[15]
        + m[9] * m[7] * m[14]
        + m[13] * m[6] * m[11]
        - m[13] * m[7] * m[10]
    )
    inv[4] = (
        -m[4] * m[10] * m[15]
        + m[4] * m[11] * m[14]
        + m[8] * m[6] * m[15]
        - m[8] * m[7] * m[14]
        - m[12] * m[6] * m[11]
        + m[12] * m[7] * m[10]
    )
    inv[8] = (
        m[4] * m[9] * m[15]
        - m[4] * m[11] * m[13]
        - m[8] * m[5] * m[15]
        + m[8] * m[7] * m[13]
        + m[12] * m[5] * m[11]
        - m[12] * m[7] * m[9]
    )
    inv[12] = (
        -m[4] * m[9] * m[14]
        + m[4] * m[10] * m[13]
        + m[8] * m[5] * m[14]
        - m[8] * m[6] * m[13]
        - m[12] * m[5] * m[10]
        + m[12] * m[6] * m[9]
    )

    det = m[0] * inv[0] + m[1] * inv[4] + m[2] * inv[8] + m[3] * inv[12]
    if abs(det) < DETERMINANT_EPSILON:
        return [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

    inv[1] = (
        -m[1] * m[10] * m[15]
        + m[1] * m[11] * m[14]
        + m[9] * m[2] * m[15]
        - m[9] * m[3] * m[14]
        - m[13] * m[2] * m[11]
        + m[13] * m[3] * m[10]
    )
    inv[5] = (
        m[0] * m[10] * m[15]
        - m[0] * m[11] * m[14]
        - m[8] * m[2] * m[15]
        + m[8] * m[3] * m[14]
        + m[12] * m[2] * m[11]
        - m[12] * m[3] * m[10]
    )
    inv[9] = (
        -m[0] * m[9] * m[15]
        + m[0] * m[11] * m[13]
        + m[8] * m[1] * m[15]
        - m[8] * m[3] * m[13]
        - m[12] * m[1] * m[11]
        + m[12] * m[3] * m[9]
    )
    inv[13] = (
        m[0] * m[9] * m[14]
        - m[0] * m[10] * m[13]
        - m[8] * m[1] * m[14]
        + m[8] * m[2] * m[13]
        + m[12] * m[1] * m[10]
        - m[12] * m[2] * m[9]
    )

    inv[2] = (
        m[1] * m[6] * m[15]
        - m[1] * m[7] * m[14]
        - m[5] * m[2] * m[15]
        + m[5] * m[3] * m[14]
        + m[13] * m[2] * m[7]
        - m[13] * m[3] * m[6]
    )
    inv[6] = (
        -m[0] * m[6] * m[15]
        + m[0] * m[7] * m[14]
        + m[4] * m[2] * m[15]
        - m[4] * m[3] * m[14]
        - m[12] * m[2] * m[7]
        + m[12] * m[3] * m[6]
    )
    inv[10] = (
        m[0] * m[5] * m[15]
        - m[0] * m[7] * m[13]
        - m[4] * m[1] * m[15]
        + m[4] * m[3] * m[13]
        + m[12] * m[1] * m[7]
        - m[12] * m[3] * m[5]
    )
    inv[14] = (
        -m[0] * m[5] * m[14]
        + m[0] * m[6] * m[13]
        + m[4] * m[1] * m[14]
        - m[4] * m[2] * m[13]
        - m[12] * m[1] * m[6]
        + m[12] * m[2] * m[5]
    )

    inv[3] = (
        -m[1] * m[6] * m[11]
        + m[1] * m[7] * m[10]
        + m[5] * m[2] * m[11]
        - m[5] * m[3] * m[10]
        - m[9] * m[2] * m[7]
        + m[9] * m[3] * m[6]
    )
    inv[7] = (
        m[0] * m[6] * m[11]
        - m[0] * m[7] * m[10]
        - m[4] * m[2] * m[11]
        + m[4] * m[3] * m[10]
        + m[8] * m[2] * m[7]
        - m[8] * m[3] * m[6]
    )
    inv[11] = (
        -m[0] * m[5] * m[11]
        + m[0] * m[7] * m[9]
        + m[4] * m[1] * m[11]
        - m[4] * m[3] * m[9]
        - m[8] * m[1] * m[7]
        + m[8] * m[3] * m[5]
    )
    inv[15] = (
        m[0] * m[5] * m[10]
        - m[0] * m[6] * m[9]
        - m[4] * m[1] * m[10]
        + m[4] * m[2] * m[9]
        + m[8] * m[1] * m[6]
        - m[8] * m[2] * m[5]
    )

    inverse_determinant = 1.0 / det
    return [x * inverse_determinant for x in inv]


def _build_mesh_empty() -> dict:
    """Build a minimal glTF mesh with no geometry."""
    return {"primitives": [{"attributes": {}, "mode": 4}]}


def _build_mesh_static(mef: MEF, builder: _GltfBufferBuilder) -> dict:
    """Build glTF mesh for static model (type 0)."""
    vertices = mef.xtrv.content_0
    if not vertices:
        return _build_mesh_empty()
    positions = [_position_to_gltf(v.position_x, v.position_y, v.position_z) for v in vertices]
    normals = [_normal_to_gltf(v.normal_x, v.normal_y, v.normal_z) for v in vertices]
    uvs = [(v.uv_u, 1.0 - v.uv_v) for v in vertices]

    position_accessor = builder.add_vec3_accessor(positions)
    normal_accessor = builder.add_vec3_accessor(normals)
    uv_accessor = builder.add_vec2_accessor(uvs)

    primitives = _build_primitives(mef, builder, position_accessor, normal_accessor, uv_accessor)
    return {"primitives": primitives}


def _build_mesh_skeletal(mef: MEF, builder: _GltfBufferBuilder) -> dict:
    """Build glTF mesh for skeletal model (type 1) with skinning attributes."""
    vertices = mef.xtrv.content_1
    if not vertices:
        return _build_mesh_empty()
    positions = [_position_to_gltf(v.position_x, v.position_y, v.position_z) for v in vertices]
    normals = [_normal_to_gltf(v.normal_x, v.normal_y, v.normal_z) for v in vertices]
    uvs = [(v.uv_u, 1.0 - v.uv_v) for v in vertices]

    position_accessor = builder.add_vec3_accessor(positions)
    normal_accessor = builder.add_vec3_accessor(normals)
    uv_accessor = builder.add_vec2_accessor(uvs)

    # Skinning: each vertex has one bone with a weight
    joints_data: list[tuple[int, int, int, int]] = []
    weights_data: list[tuple[float, float, float, float]] = []
    for v in vertices:
        joints_data.append((v.bone_index, 0, 0, 0))
        weights_data.append((v.bone_weight, 1.0 - v.bone_weight, 0.0, 0.0))

    joints_accessor = builder.add_vec4_u16_accessor(joints_data)
    weights_accessor = builder.add_vec4_accessor(weights_data)

    primitives = _build_primitives(
        mef,
        builder,
        position_accessor,
        normal_accessor,
        uv_accessor,
        joints_accessor=joints_accessor,
        weights_accessor=weights_accessor,
    )
    return {"primitives": primitives}


def _build_mesh_building(mef: MEF, builder: _GltfBufferBuilder) -> dict:
    """Build glTF mesh for building model (type 3) — positions only."""
    vertices = mef.xtrv.content_3
    if not vertices:
        return _build_mesh_empty()
    positions = [_position_to_gltf(v.position_x, v.position_y, v.position_z) for v in vertices]
    position_accessor = builder.add_vec3_accessor(positions)
    primitives = _build_primitives(mef, builder, position_accessor, normal_accessor=None, uv_accessor=None)
    return {"primitives": primitives}


def _build_mesh_sems(mef: MEF, builder: _GltfBufferBuilder) -> dict:
    """Build glTF mesh for SEMS variant (simplified collision mesh)."""
    positions = [_position_to_gltf(v.position_x, v.position_y, v.position_z) for v in mef.xtvs.content]
    position_accessor = builder.add_vec3_accessor(positions)

    indices = []
    for face in mef.cafs.content:
        indices.extend([face.index_a, face.index_b, face.index_c])

    if not indices:
        return {"primitives": [{"attributes": {"POSITION": position_accessor}, "mode": 4}]}

    index_accessor = builder.add_indices_accessor(indices)
    return {"primitives": [{"attributes": {"POSITION": position_accessor}, "indices": index_accessor, "mode": 4}]}


def _build_primitives(  # noqa: C901, PLR0912, PLR0913
    mef: MEF,
    builder: _GltfBufferBuilder,
    position_accessor: int,
    normal_accessor: int | None,
    uv_accessor: int | None,
    *,
    joints_accessor: int | None = None,
    weights_accessor: int | None = None,
) -> list[dict]:
    """Build glTF primitives split by DNER render groups."""
    attributes: dict = {"POSITION": position_accessor}
    if normal_accessor is not None:
        attributes["NORMAL"] = normal_accessor
    if uv_accessor is not None:
        attributes["TEXCOORD_0"] = uv_accessor
    if joints_accessor is not None:
        attributes["JOINTS_0"] = joints_accessor
    if weights_accessor is not None:
        attributes["WEIGHTS_0"] = weights_accessor

    if mef.ecaf is None:
        return [{"attributes": attributes, "mode": 4}]

    # Collect all face indices
    all_indices = []
    for face in mef.ecaf.content:
        all_indices.extend([face.index_a, face.index_b, face.index_c])

    if not all_indices:
        return [{"attributes": attributes, "mode": 4}]

    # Try to split by render groups from DNER
    model_type = mef.hsem.model_type
    groups = None
    if mef.dner is not None:
        if model_type == MODEL_TYPE_STATIC:
            groups = mef.dner.content_0
        elif model_type == MODEL_TYPE_SKELETAL:
            groups = mef.dner.content_1
        elif model_type == MODEL_TYPE_BUILDING:
            groups = mef.dner.content_3

    if groups is None or len(groups) <= 1:
        index_accessor = builder.add_indices_accessor(all_indices)
        return [{"attributes": attributes, "indices": index_accessor, "mode": 4}]

    # Split faces by render group
    primitives: list[dict] = []
    for group in groups:
        start = group.index_start * 3
        count = group.face_count * 3
        group_indices = all_indices[start : start + count]
        if not group_indices:
            continue
        index_accessor = builder.add_indices_accessor(group_indices)
        primitives.append({"attributes": attributes, "indices": index_accessor, "mode": 4})

    if not primitives:
        index_accessor = builder.add_indices_accessor(all_indices)
        return [{"attributes": attributes, "indices": index_accessor, "mode": 4}]

    return primitives


def mef_to_gltf(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_path: Path | None = source_path.with_suffix(".gltf") if source_path is not None else None
    mef = MEF.model_validate_stream(source_io)

    builder = _GltfBufferBuilder()

    # SEMS variant
    if mef.is_sems_variant:
        mesh = _build_mesh_sems(mef, builder)
        nodes: list[dict] = [{"name": "mesh", "mesh": 0}]
        scene_nodes = [0]
        skin = None
    else:
        model_type = mef.hsem.model_type

        if model_type == MODEL_TYPE_SKELETAL:
            mesh = _build_mesh_skeletal(mef, builder)
        elif model_type == MODEL_TYPE_BUILDING:
            mesh = _build_mesh_building(mef, builder)
        else:
            mesh = _build_mesh_static(mef, builder)

        # Build skeleton for skeletal models
        if model_type == MODEL_TYPE_SKELETAL and mef.reih is not None and mef.manb is not None:
            skeleton_nodes, skeleton_roots, skin, _ = _build_skeleton(mef, builder)

            # Mesh node comes after skeleton nodes
            mesh_node_idx = len(skeleton_nodes)
            mesh_node: dict = {"name": "mesh", "mesh": 0}
            if skin is not None:
                mesh_node["skin"] = 0
            skeleton_nodes.append(mesh_node)

            nodes = skeleton_nodes
            scene_nodes = [*skeleton_roots, mesh_node_idx]
        else:
            nodes = [{"name": "mesh", "mesh": 0}]
            scene_nodes = [0]
            skin = None

    # Assemble glTF
    name = source_path.stem if source_path else "mef_model"
    gltf: dict = {
        "asset": {"version": "2.0", "generator": "igipy"},
        "scene": 0,
        "scenes": [{"name": name, "nodes": scene_nodes}],
        "nodes": nodes,
        "meshes": [mesh],
    }

    if skin is not None:
        gltf["skins"] = [skin]

    if builder.buffer_views:
        buffer_bytes = bytes(builder.buffer)
        gltf["buffers"] = [{"uri": _make_data_uri(buffer_bytes), "byteLength": len(buffer_bytes)}]
        gltf["bufferViews"] = builder.buffer_views
        gltf["accessors"] = builder.accessors

    target_io = BytesIO()
    target_io.write(json.dumps(gltf, indent=2).encode("utf-8"))
    target_io.seek(0)
    return target_io, target_path
