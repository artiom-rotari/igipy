"""Export MEF 3D model to FBX 7.5 ASCII format.

Produces a triangle mesh with positions, normals, and UVs. Skeletal models
(type 1) include bone hierarchy, skinning weights, and a bind pose. The
result can be imported into Unity, Blender, Maya, or any FBX-compatible tool.
"""

import math
from collections import defaultdict
from io import BytesIO
from pathlib import Path

from igipy.core.formats.fbx import (
    FBX,
    FBXCluster,
    FBXConnection,
    FBXGeometry,
    FBXMaterial,
    FBXModel,
    FBXNodeAttribute,
    FBXPose,
    FBXPoseNode,
    FBXSkin,
    IdGenerator,
)
from igipy.igi2.formats.mef import MEF
from igipy.igi2.services.iff_to_fbx import (
    ATTA_NO_BONE,
    _position_to_fbx,
)

MODEL_TYPE_STATIC = 0
MODEL_TYPE_SKELETAL = 1
MODEL_TYPE_BUILDING = 3


def _normal_to_fbx(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Convert normal from IGI2 Z-up to FBX Y-up (no scale)."""
    return x, z, -y


def _rotation_matrix_to_euler(  # noqa: PLR0913
    m00: float,
    m01: float,
    m02: float,
    m10: float,
    m11: float,
    m12: float,
    m20: float,
    m21: float,
    m22: float,
) -> tuple[float, float, float]:
    """Convert 3x3 rotation matrix (IGI2 Z-up) to FBX Y-up Euler XYZ degrees.

    Applies coordinate system conversion P * R * P^T where
    P = [[1,0,0],[0,0,1],[0,-1,0]] (Z-up -> Y-up).
    """
    r00, r01, r02 = m00, m02, -m01  # noqa: F841
    r10, r11, r12 = m20, m22, -m21
    r20, r21, r22 = -m10, -m12, m11

    if abs(r20) < 0.99999:  # noqa: PLR2004
        pitch = math.asin(max(-1.0, min(1.0, -r20)))
        roll = math.atan2(r21, r22)
        yaw = math.atan2(r10, r00)
    else:
        pitch = math.copysign(math.pi / 2, -r20)
        roll = math.atan2(-r12, r11)
        yaw = 0.0

    return math.degrees(roll), math.degrees(pitch), math.degrees(yaw)


# ---------------------------------------------------------------------------
# Skinning helpers
# ---------------------------------------------------------------------------


def _compute_world_transforms(
    bone_count: int,
    rest_offsets: list[tuple[float, float, float]],
    parents: list[int],
) -> list[list[float]]:
    """Compute 4x4 row-major world transform for each bone."""
    world_transforms: list[list[float]] = []
    for i in range(bone_count):
        if i < len(rest_offsets):
            translation_x, translation_y, translation_z = _position_to_fbx(*rest_offsets[i])
        else:
            translation_x, translation_y, translation_z = 0.0, 0.0, 0.0
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
            translation_x,
            translation_y,
            translation_z,
            1,
        ]
        parent_index = parents[i]
        world = (
            _mat4_mul_row(world_transforms[parent_index], local) if 0 <= parent_index < len(world_transforms) else local
        )
        world_transforms.append(world)
    return world_transforms


def _mat4_mul_row(a: list[float], b: list[float]) -> list[float]:
    """Multiply two 4x4 row-major matrices."""
    r = [0.0] * 16
    for row in range(4):
        for col in range(4):
            s = 0.0
            for k in range(4):
                s += a[row * 4 + k] * b[k * 4 + col]
            r[row * 4 + col] = s
    return r


def _mat4_inverse_row(m: list[float]) -> list[float]:
    """Invert a 4x4 row-major matrix. Falls back to identity on singular."""
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
    if abs(det) < 1e-15:  # noqa: PLR2004
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


# ---------------------------------------------------------------------------
# Geometry extraction helpers
# ---------------------------------------------------------------------------


def _extract_static(
    mef: MEF,
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[int, int, int]],
    list[tuple[float, float, float]] | None,
    list[tuple[float, float]] | None,
]:
    """Extract positions, faces, normals, uvs for static model (type 0)."""
    vertices = mef.xtrv.content_0
    positions = [_position_to_fbx(v.position_x, v.position_y, v.position_z) for v in vertices]
    normals = [_normal_to_fbx(v.normal_x, v.normal_y, v.normal_z) for v in vertices]
    uvs = [(v.uv_u, 1.0 - v.uv_v) for v in vertices]
    faces = [(f.index_a, f.index_b, f.index_c) for f in mef.ecaf.content]
    return positions, faces, normals, uvs


def _extract_skeletal(
    mef: MEF,
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[int, int, int]],
    list[tuple[float, float, float]] | None,
    list[tuple[float, float]] | None,
]:
    """Extract positions, faces, normals, uvs for skeletal model (type 1)."""
    vertices = mef.xtrv.content_1
    positions = [_position_to_fbx(v.position_x, v.position_y, v.position_z) for v in vertices]
    normals = [_normal_to_fbx(v.normal_x, v.normal_y, v.normal_z) for v in vertices]
    uvs = [(v.uv_u, 1.0 - v.uv_v) for v in vertices]
    faces = [(f.index_a, f.index_b, f.index_c) for f in mef.ecaf.content]
    return positions, faces, normals, uvs


def _extract_building(
    mef: MEF,
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[int, int, int]],
    None,
    list[tuple[float, float]] | None,
]:
    """Extract positions, faces, and diffuse UVs for building model (type 3).

    Type-3 vertices carry a diffuse UV set (decoded from the editor's text-MEF sources)
    but no per-vertex normal — lighting is baked into the lightmap — so normals stay None.
    ``v.uv_v`` reconstructs the raw source V from the pre-flipped stored value, so the same
    ``(uv_u, 1.0 - uv_v)`` convention as type 0/1 applies.
    """
    vertices = mef.xtrv.content_3
    positions = [_position_to_fbx(v.position_x, v.position_y, v.position_z) for v in vertices]
    uvs = [(v.uv_u, 1.0 - v.uv_v) for v in vertices]
    faces = [(f.index_a, f.index_b, f.index_c) for f in mef.ecaf.content]
    return positions, faces, None, uvs


def _extract_sems(
    mef: MEF,
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[int, int, int]],
    None,
    None,
]:
    """Extract positions and faces for SEMS variant."""
    positions = [_position_to_fbx(v.position_x, v.position_y, v.position_z) for v in mef.xtvs.content]
    faces = [(f.index_a, f.index_b, f.index_c) for f in mef.cafs.content]
    return positions, faces, None, None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def mef_to_fbx(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:  # noqa: C901, PLR0912, PLR0915
    target_path: Path | None = source_path.with_suffix(".fbx") if source_path is not None else None
    mef = MEF.model_validate_stream(source_io)

    name = source_path.stem if source_path else "mef_model"
    id_gen = IdGenerator()

    # Determine model type and extract geometry
    is_sems = mef.is_sems_variant
    model_type = 0 if is_sems else mef.hsem.model_type
    is_skeletal = not is_sems and model_type == MODEL_TYPE_SKELETAL

    if is_sems:
        positions, faces, normals, uvs = _extract_sems(mef)
    elif model_type == MODEL_TYPE_SKELETAL:
        positions, faces, normals, uvs = _extract_skeletal(mef)
    elif model_type == MODEL_TYPE_BUILDING:
        positions, faces, normals, uvs = _extract_building(mef)
    else:
        positions, faces, normals, uvs = _extract_static(mef)

    # Core objects
    geometry_id = id_gen()
    material_id = id_gen()
    mesh_model_id = id_gen()

    geometries = [FBXGeometry(id=geometry_id, name=name, positions=positions, faces=faces, normals=normals, uvs=uvs)]
    materials = [FBXMaterial(id=material_id, name=name)]
    node_attributes: list[FBXNodeAttribute] = []
    models: list[FBXModel] = [FBXModel(id=mesh_model_id, name=name, type="Mesh")]
    skins: list[FBXSkin] = []
    poses: list[FBXPose] = []
    connections: list[FBXConnection] = []

    # Geometry -> Mesh Model, Material -> Mesh Model, Mesh Model -> scene root
    connections.append(FBXConnection(source=geometry_id, destination=mesh_model_id))
    connections.append(FBXConnection(source=material_id, destination=mesh_model_id))
    connections.append(FBXConnection(source=mesh_model_id, destination=0))

    # Skeleton setup
    bone_count = 0
    bone_names: list[str] = []
    bone_ids: list[int] = []
    rest_offsets: list[tuple[float, float, float]] = []
    parents: list[int] = []
    world_transforms: list[list[float]] = []

    if is_skeletal and mef.reih is not None and mef.manb is not None:
        rest_offsets = mef.reih.bones_offsets
        bone_count = len(mef.reih.content)
        parents = mef.reih.bones_parents
        bone_names = mef.manb.content[:bone_count]
        bone_ids = [id_gen() for _ in range(bone_count)]
        bone_attribute_ids = [id_gen() for _ in range(bone_count)]
        world_transforms = _compute_world_transforms(bone_count, rest_offsets, parents)

        for i in range(bone_count):
            node_attributes.append(
                FBXNodeAttribute(
                    id=bone_attribute_ids[i],
                    name=bone_names[i],
                    type="LimbNode",
                    type_flags="Skeleton",
                )
            )
            translation = _position_to_fbx(*rest_offsets[i]) if i < len(rest_offsets) else (0.0, 0.0, 0.0)
            models.append(FBXModel(id=bone_ids[i], name=bone_names[i], type="LimbNode", translation=translation))

        # Bone connections: NodeAttribute -> Model, bone hierarchy
        connections.extend(
            FBXConnection(source=bone_attribute_ids[i], destination=bone_ids[i]) for i in range(bone_count)
        )
        for i in range(bone_count):
            parent_id = 0 if parents[i] == -1 else bone_ids[parents[i]]
            connections.append(FBXConnection(source=bone_ids[i], destination=parent_id))

        # Skin deformers
        skin_id = id_gen()
        cluster_ids = [id_gen() for _ in range(bone_count)]

        # Group vertices by bone
        bone_verts: dict[int, list[int]] = defaultdict(list)
        bone_weights: dict[int, list[float]] = defaultdict(list)
        for vi, v in enumerate(mef.xtrv.content_1):
            bone_verts[v.bone_index].append(vi)
            bone_weights[v.bone_index].append(v.bone_weight)

        clusters: list[FBXCluster] = []
        for bi in range(bone_count):
            inverse_bind = _mat4_inverse_row(world_transforms[bi])
            clusters.append(
                FBXCluster(
                    id=cluster_ids[bi],
                    name=bone_names[bi],
                    indexes=bone_verts.get(bi, []),
                    weights=bone_weights.get(bi, []),
                    transform=inverse_bind,
                    transform_link=world_transforms[bi],
                )
            )

        skins.append(FBXSkin(id=skin_id, name=name, clusters=clusters))

        # Skin connections: Skin -> Geometry, Cluster -> Skin, Bone -> Cluster
        connections.append(FBXConnection(source=skin_id, destination=geometry_id))
        for i in range(bone_count):
            connections.append(FBXConnection(source=cluster_ids[i], destination=skin_id))
            connections.append(FBXConnection(source=bone_ids[i], destination=cluster_ids[i]))

        # Bind pose
        pose_id = id_gen()
        pose_nodes = [FBXPoseNode(node_id=mesh_model_id, matrix=[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])]
        pose_nodes.extend(FBXPoseNode(node_id=bone_ids[i], matrix=world_transforms[i]) for i in range(bone_count))
        poses.append(FBXPose(id=pose_id, name=name, nodes=pose_nodes))

    # Attachments
    if mef.atta is not None:
        attachment_ids = [id_gen() for _ in range(len(mef.atta.content))]
        attachment_attribute_ids = [id_gen() for _ in range(len(mef.atta.content))]

        for i, item in enumerate(mef.atta.content):
            attachment_name = "attach_" + item.name.rstrip(b"\x00").decode("ascii", errors="replace")
            translation_x, translation_y, translation_z = _position_to_fbx(
                item.position_x, item.position_y, item.position_z
            )
            rotation_x, rotation_y, rotation_z = _rotation_matrix_to_euler(
                item.m00,
                item.m01,
                item.m02,
                item.m10,
                item.m11,
                item.m12,
                item.m20,
                item.m21,
                item.m22,
            )
            node_attributes.append(
                FBXNodeAttribute(id=attachment_attribute_ids[i], name=attachment_name, type="Null", type_flags="Null")
            )
            models.append(
                FBXModel(
                    id=attachment_ids[i],
                    name=attachment_name,
                    type="Null",
                    translation=(translation_x, translation_y, translation_z),
                    rotation=(rotation_x, rotation_y, rotation_z),
                )
            )

        # Attachment connections: NodeAttribute -> Model, Attachment -> parent
        connections.extend(
            FBXConnection(source=attachment_attribute_ids[i], destination=attachment_ids[i])
            for i in range(len(mef.atta.content))
        )
        for i, item in enumerate(mef.atta.content):
            if item.bone_index != ATTA_NO_BONE and bone_ids and 0 <= item.bone_index < bone_count:
                connections.append(FBXConnection(source=attachment_ids[i], destination=bone_ids[item.bone_index]))
            else:
                connections.append(FBXConnection(source=attachment_ids[i], destination=0))

    fbx = FBX(
        name=name,
        geometries=geometries,
        materials=materials,
        node_attributes=node_attributes,
        models=models,
        skins=skins,
        poses=poses,
        connections=connections,
    )

    target_io, _ = fbx.model_dump_stream()
    return target_io, target_path
